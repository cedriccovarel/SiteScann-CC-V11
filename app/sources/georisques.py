"""Géorisques (API v1) : chaque réponse est lue champ par champ.

Une réponse dont les champs attendus sont absents n'est jamais interprétée : elle est signalée
« non interprétée » pour vérification sur georisques.gouv.fr.
Documentation des endpoints : https://www.georisques.gouv.fr/doc-api
"""
import asyncio

from app.config import GEORISQUES_URL
from app.http import Client
from app.models import Ligne, Lieu
from app.sources import nom_de

SOURCE = "Géorisques"
NON_INTERPRETEE = "Réponse non interprétée : consulter georisques.gouv.fr"

# Recensements autour du point : clé -> (endpoint, libellé, rayon de recherche en m)
RECENSEMENTS = {
    "icpe": ("/installations_classees", "Installations classées (ICPE)", 1000),
    "cavites": ("/cavites", "Cavités souterraines", 500),
    "mvt": ("/mvt", "Mouvements de terrain recensés", 500),
    "sis": ("/ssp/conclusions_sis", "Secteurs d'information sur les sols (SIS)", 500),
    "casias": ("/ssp/casias", "Anciens sites industriels et activités de service (CASIAS)", 500),
    "instructions": ("/ssp/instructions", "Sites pollués ou potentiellement pollués (ex-BASOL)", 500),
}


def _data(payload) -> list | None:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    return None


def _indisponible(libelle: str, payload, detail: str = "") -> Ligne:
    texte = detail or ("Service indisponible" if payload is None else NON_INTERPRETEE)
    return Ligne(libelle=libelle, resultat=texte, statut="indisponible", source=SOURCE)


def _premiere_valeur(payload, *cles: str) -> str | None:
    """Valeur du premier champ trouvé, dans l'objet lui-même ou dans le premier élément de « data »."""
    candidats = [payload] if isinstance(payload, dict) else []
    candidats += (_data(payload) or [])[:1]
    for obj in candidats:
        for cle in cles:
            if isinstance(obj, dict) and obj.get(cle) not in (None, ""):
                return str(obj[cle])
    return None


def lire_sismicite(payload) -> Ligne:
    libelle = "Zonage sismique"
    zone = _premiere_valeur(payload, "zone_sismicite", "code_zone")
    if zone is None:
        return _indisponible(libelle, payload)
    return Ligne(libelle=libelle, resultat=zone if "zone" in zone.lower() else f"Zone {zone}", statut="donnee", source=SOURCE)


def lire_radon(payload) -> Ligne:
    libelle = "Potentiel radon (commune)"
    classe = _premiere_valeur(payload, "classe_potentiel")
    if classe is None:
        return _indisponible(libelle, payload)
    return Ligne(libelle=libelle, resultat=f"Catégorie {classe}", statut="donnee", source=SOURCE)


def lire_rga(payload) -> Ligne:
    libelle = "Retrait-gonflement des argiles"
    exposition = _premiere_valeur(payload, "exposition")
    if exposition is None:
        return _indisponible(libelle, payload)
    return Ligne(libelle=libelle, resultat=exposition, statut="donnee", source=SOURCE)


def lire_risques_commune(payload) -> Ligne:
    libelle = "Risques recensés sur la commune (GASPAR)"
    data = _data(payload)
    if data is None:
        return _indisponible(libelle, payload)
    risques = sorted({r.get("libelle_risque_long", "") for c in data for r in c.get("risques_detail", [])} - {""})
    resultat = ", ".join(risques) if risques else "Aucun risque recensé dans la base GASPAR pour la commune"
    return Ligne(libelle=libelle, resultat=resultat, statut="donnee", source=SOURCE)


def lire_recensement(cle: str, payload) -> Ligne:
    _, libelle, rayon = RECENSEMENTS[cle]
    libelle = f"{libelle} – {rayon} m"
    data = _data(payload)
    if data is None:
        return _indisponible(libelle, payload)
    total = payload.get("results", len(data)) if isinstance(payload.get("results"), int) else len(data)
    if not total:
        return Ligne(libelle=libelle, resultat="Aucun recensé dans ce rayon", statut="donnee", source=SOURCE)
    noms = [n for n in (nom_de(d) for d in data[:5]) if n]
    resultat = f"{total} recensé(s)" + (f" : {', '.join(noms)}" + (" …" if total > len(noms) else "") if noms else "")
    return Ligne(libelle=libelle, resultat=resultat, statut="donnee", source=SOURCE)


async def interroger(client: Client, lieu: Lieu) -> dict[str, Ligne]:
    latlon = f"{lieu.lon},{lieu.lat}"
    insee = {"code_insee": lieu.code_insee} if lieu.code_insee else None

    async def get(path: str, params: dict | None):
        if params is None:
            return None
        return await client.json(f"{SOURCE} {path}", f"{GEORISQUES_URL}{path}", params)

    cles = list(RECENSEMENTS)
    reponses = await asyncio.gather(
        get("/zonage_sismique", {"latlon": latlon}),
        get("/rga", {"latlon": latlon}),
        get("/radon", insee),
        get("/gaspar/risques", insee),
        *(get(RECENSEMENTS[c][0], {"latlon": latlon, "rayon": RECENSEMENTS[c][2]}) for c in cles),
    )
    sismicite, rga, radon, gaspar, *recensements = reponses
    lignes = {
        "sismicite": lire_sismicite(sismicite),
        "rga": lire_rga(rga),
        "radon": lire_radon(radon) if insee else _indisponible("Potentiel radon (commune)", None, "Code INSEE inconnu"),
        "risques_commune": lire_risques_commune(gaspar) if insee
        else _indisponible("Risques recensés sur la commune (GASPAR)", None, "Code INSEE inconnu"),
    }
    lignes.update({c: lire_recensement(c, p) for c, p in zip(cles, recensements)})
    return lignes
