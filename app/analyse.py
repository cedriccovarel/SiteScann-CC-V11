"""Analyse d'un site et construction du rapport, exigence BEE par exigence.

Les textes et pièces justificatives viennent de referentiel/bee.json (extrait du catalogue de
l'Observatoire). Les seuils de distance utilisés ci-dessous sont ceux écrits dans ces textes.
"""
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import shape

from app.config import SCORE_GEOCODAGE_MIN
from app.geo import Repere
from app.http import Client
from app.models import Analyse, Demande, Element, Exigence, Ligne, Lieu, Rubrique
from app.sources import apicarto, geocodage, georisques, osm
from app.sources.osm import PAR_CLE

REFERENTIEL = json.loads((Path(__file__).parent / "referentiel" / "bee.json").read_text(encoding="utf-8"))
ORDRE = ("analyse_site", "eco_mobilite", "modes_doux", "localisation_seniors", "dechets_menagers",
         "acoustique_avant_travaux")
API_CARTO = "API Carto IGN"


@dataclass
class Donnees:
    """Tout ce qui a été collecté pour un site ; None = source indisponible."""
    lieu: Lieu
    parcelle: dict | None
    osm: list[Element] | None
    risques: dict[str, Ligne]
    nature: dict[str, list[str] | None]
    zones_urba: list[dict] | None
    servitudes: list[dict] | None

    def osm_de(self, *categories: str, max_m: int | None = None) -> list[Element] | None:
        if self.osm is None:
            return None
        return [e for e in self.osm if e.categorie in categories and (max_m is None or e.distance_m <= max_m)]


# ---------------------------------------------------------------- lignes génériques

def a_completer(libelle: str, resultat: str, source: str = "") -> Ligne:
    return Ligne(libelle=libelle, resultat=resultat, statut="a_completer", source=source)


def _nom(e: Element) -> str:
    return e.nom or PAR_CLE[e.categorie].libelle.lower() + " sans nom"


def ligne_osm(libelle: str, elements: list[Element] | None, vide: str = "Aucun élément recensé") -> Ligne:
    if elements is None:
        return Ligne(libelle=libelle, resultat="OpenStreetMap n'a pas répondu", statut="indisponible", source=osm.SOURCE)
    if not elements:
        return Ligne(libelle=libelle, resultat=f"{vide} dans OpenStreetMap", statut="absent", source=osm.SOURCE)
    proche = min(elements, key=lambda e: e.distance_m)
    resultat = f"{len(elements)} élément(s) ; le plus proche : {_nom(proche)} à {proche.distance_m} m"
    return Ligne(libelle=libelle, resultat=resultat, statut="indicatif", source=osm.SOURCE, elements=elements)


def ligne_seuil(libelle: str, elements: list[Element] | None, seuil_m: int) -> Ligne:
    """Présence d'au moins un élément sous le seuil du référentiel (selon les données disponibles)."""
    if elements is None:
        return ligne_osm(libelle, None)
    proches = [e for e in elements if e.distance_m <= seuil_m]
    if not proches:
        return Ligne(libelle=libelle, resultat=f"Aucun trouvé à moins de {seuil_m} m : justificatif à fournir",
                     statut="absent", source=osm.SOURCE)
    proche = proches[0]
    return Ligne(libelle=libelle, resultat=f"Oui : {_nom(proche)} à {proche.distance_m} m (vol d'oiseau)",
                 statut="indicatif", source=osm.SOURCE, elements=proches)


def ligne_nature(d: Donnees) -> Ligne:
    libelle = "Natura 2000 et ZNIEFF – 500 m"
    if all(v is None for v in d.nature.values()):
        return Ligne(libelle=libelle, resultat="API Carto n'a pas répondu", statut="indisponible", source=API_CARTO)
    trouvees = [f"{apicarto.NATURE[c]} : {', '.join(noms)}" for c, noms in d.nature.items() if noms]
    manquantes = [apicarto.NATURE[c] for c, noms in d.nature.items() if noms is None]
    resultat = " ; ".join(trouvees) or "Aucune zone dans un rayon de 500 m"
    if manquantes:
        resultat += f" (non interrogé : {', '.join(manquantes)})"
    return Ligne(libelle=libelle, resultat=resultat, statut="donnee", source=API_CARTO)


def ligne_monuments(d: Donnees) -> Ligne:
    libelle = "Monuments historiques (servitude AC1)"
    if d.servitudes is None:
        return Ligne(libelle=libelle, resultat="Géoportail de l'Urbanisme n'a pas répondu", statut="indisponible",
                     source=API_CARTO)
    ac1 = [s for s in d.servitudes if str(s.get("suptype", "")).lower().startswith("ac1")]
    if ac1:
        noms = ", ".join(sorted({n for n in (s.get("nomsuplitt") or s.get("nomsup") or "" for s in ac1) if n}))
        return Ligne(libelle=libelle, resultat="Site dans un périmètre de protection" + (f" : {noms}" if noms else ""),
                     statut="donnee", source=API_CARTO)
    return Ligne(libelle=libelle, resultat="Aucune servitude AC1 numérisée au point (les servitudes ne sont pas "
                 "toutes publiées : vérifier en mairie)", statut="absent", source=API_CARTO)


def ligne_urbanisme(d: Donnees) -> Ligne:
    libelle = "Document d'urbanisme et servitudes au point"
    if d.zones_urba is None:
        return Ligne(libelle=libelle, resultat="Géoportail de l'Urbanisme n'a pas répondu", statut="indisponible",
                     source=API_CARTO)
    zones = [" – ".join(x for x in (z.get("libelle"), z.get("libelong")) if x) for z in d.zones_urba]
    sup = sorted({str(s.get("suptype", "")).upper() for s in d.servitudes or [] if s.get("suptype")})
    if not zones:
        return Ligne(libelle=libelle, resultat="Aucun zonage publié au Géoportail de l'Urbanisme (RNU ou document "
                     "non numérisé) : consulter la mairie", statut="absent", source=API_CARTO)
    resultat = "Zone " + " ; ".join(zones) + (f" ; servitudes : {', '.join(sup)}" if sup else "")
    return Ligne(libelle=libelle, resultat=resultat, statut="donnee", source=API_CARTO)


def ligne_projet(d: Donnees) -> Ligne:
    if not d.parcelle:
        return a_completer("Le projet (bâtiment)", f"Point d'adresse : {d.lieu.libelle} ; parcelle non identifiée")
    p = d.parcelle.get("properties", {})
    ref = " ".join(str(x) for x in (p.get("code_insee") or p.get("commune"), p.get("section"), p.get("numero")) if x)
    surface = f" ; contenance cadastrale {p['contenance']} m²" if p.get("contenance") else ""
    return Ligne(libelle="Le projet (bâtiment)", resultat=f"Parcelle {ref}{surface} ; emprise du bâtiment à dessiner",
                 statut="donnee", source="Cadastre (API Carto IGN)")


# ---------------------------------------------------------------- exigences

def analyse_site(d: Donnees, kind: str) -> list[Rubrique]:
    r = d.risques
    pieces = REFERENTIEL[kind]["analyse_site"]["pieces"]
    return [
        Rubrique(titre="1/ Schéma de fonctionnement du site – 500 m", piece=pieces[0], schema_site=True, lignes=[
            ligne_projet(d),
            ligne_osm("Voies d'accès (100 m)", d.osm_de("route", "desserte", max_m=100)),
            Ligne(libelle="Routes, voies ferrées et sources de nuisances", resultat="Reportées sur le schéma ; liste au 2/",
                  statut="indisponible" if d.osm is None else "indicatif", source=osm.SOURCE),
            a_completer("Orientation", "Nord porté sur le schéma ; orientation des façades à indiquer par le concepteur"),
            ligne_osm("Éléments paysagers (eau, végétation)", d.osm_de("eau", "vegetation")),
            ligne_nature(d),
            ligne_osm("Autres espaces protégés (OSM)", d.osm_de("protection")),
            a_completer("Trame verte et bleue (SRCE / SRADDET)",
                        "Réservoirs et corridors à reporter depuis l'atlas régional"),
            a_completer("État des sols et masses d'eau souterraines",
                        "À renseigner (SANDRE / Eaufrance / Hub'Eau, BDLISA)"),
            a_completer("Caractéristiques géologiques", "À renseigner (carte géologique BRGM / InfoTerre)"),
        ]),
        Rubrique(titre="2/ Liste des contraintes", piece=pieces[1], lignes=[
            ligne_osm("Pollutions sonores : routes structurantes", d.osm_de("route")),
            ligne_osm("Pollutions sonores : voies ferrées", d.osm_de("voie_ferree")),
            ligne_osm("Pollutions sonores : aérodromes (3 km)", d.osm_de("aerodrome")),
            a_completer("Classement sonore des voies, cartes de bruit, PEB",
                        "À vérifier sur l'arrêté préfectoral de classement sonore et Géoportail"),
            ligne_osm("Pollutions olfactives : industrie, épuration", d.osm_de("industrie")),
            ligne_osm("Pollutions olfactives : exploitations agricoles", d.osm_de("agricole")),
            r["icpe"],
            ligne_osm("Pollutions visuelles : publicité", d.osm_de("publicite"),
                      vide="Aucun panneau recensé (recensement OSM très partiel : visite de site)"),
            ligne_osm("Pollutions électromagnétiques", d.osm_de("electromagnetique")),
            ligne_monuments(d),
            ligne_osm("Patrimoine (OSM)", d.osm_de("patrimoine")),
            ligne_urbanisme(d),
            r["risques_commune"], r["sismicite"], r["radon"],
        ]),
        Rubrique(titre="3/ Commerces, services et transports en commun – 1 km", piece=pieces[2], lignes=[
            ligne_osm("Commerces alimentaires", d.osm_de("commerce_alimentaire")),
            a_completer("Transports scolaires", "Lignes et arrêts à obtenir auprès de la mairie ou de l'autorité "
                        "organisatrice"),
            ligne_osm("Transports en commun", d.osm_de("transport_commun")),
            ligne_osm("Médecin / pharmacie", d.osm_de("soins", "pharmacie")),
            ligne_osm("Établissement scolaire / crèche", d.osm_de("enseignement")),
        ]),
        Rubrique(titre="4/ Collecte et tri des déchets ménagers", piece=pieces[3], lignes=[
            ligne_osm("Déchèteries, centres de tri et de traitement – 3 km", d.osm_de("decheterie")),
            ligne_osm("Points d'apport volontaire – 500 m", d.osm_de("apport_volontaire")),
        ]),
        Rubrique(titre="5/ Étude de sol et pollution des sols", piece=" ; ".join(pieces[4:]), lignes=[
            r["sis"], r["instructions"], r["casias"], r["rga"], r["cavites"], r["mvt"],
            a_completer("Diagnostic des sols", "Étude de sol et diagnostic pollution à faire réaliser"),
        ]),
    ]


def eco_mobilite(d: Donnees, kind: str) -> list[Rubrique]:
    return [Rubrique(titre="Questionnaire", piece=REFERENTIEL[kind]["eco_mobilite"]["pieces"][0], lignes=[
        a_completer("Questionnaire « Évaluation du potentiel éco-mobilité des bâtiments »",
                    "À renseigner par le maître d'ouvrage ; distances utiles aux 3/ de l'analyse de site et "
                    "à l'exigence « Proximité des modes doux »"),
    ])]


def modes_doux(d: Donnees, kind: str) -> list[Rubrique]:
    return [Rubrique(titre="Distances (1 km)", lignes=[
        ligne_seuil("Transports en commun à moins de 1 km", d.osm_de("transport_commun"), 1000),
        ligne_seuil("Aménagement cyclable à moins de 1 km", d.osm_de("piste_cyclable"), 1000),
    ])]


def localisation_seniors(d: Donnees, kind: str) -> list[Rubrique]:
    return [Rubrique(titre="Distances", lignes=[
        ligne_seuil("Transports en commun à moins de 500 m", d.osm_de("transport_commun"), 500),
        ligne_seuil("Commerces de base (épicerie, boulangerie, pharmacie) à moins de 500 m",
                    d.osm_de("commerce_alimentaire", "pharmacie"), 500),
        ligne_seuil("Services de soin à moins de 1 km", d.osm_de("soins"), 1000),
    ])]


def dechets_menagers(d: Donnees, kind: str) -> list[Rubrique]:
    return [Rubrique(titre="Alternatives au composteur sur la parcelle (rayon de recherche 500 m)", lignes=[
        ligne_osm("Compostage partagé", d.osm_de("compost")),
        ligne_osm("Points d'apport volontaire", d.osm_de("apport_volontaire")),
        a_completer("Collecte des biodéchets en porte à porte", "À vérifier auprès de la collectivité"),
    ])]


def acoustique_avant_travaux(d: Donnees, kind: str) -> list[Rubrique]:
    return [Rubrique(titre="Mesure", piece=REFERENTIEL[kind]["acoustique_avant_travaux"]["pieces"][0], lignes=[
        a_completer("Isolement acoustique de façade", "Mesure ou note de calcul à produire ; sources de bruit "
                    "identifiées au 2/ de l'analyse de site"),
    ])]


CONSTRUCTEURS = {f.__name__: f for f in (analyse_site, eco_mobilite, modes_doux, localisation_seniors,
                                         dechets_menagers, acoustique_avant_travaux)}


def exigences(d: Donnees, kind: str) -> list[Exigence]:
    return [
        Exigence(cle=cle, code=x["code"], titre=x["title"], referentiel=x["referential"], version=x["version"],
                 description=x["description"], rubriques=CONSTRUCTEURS[cle](d, kind))
        for cle in ORDRE if (x := REFERENTIEL[kind].get(cle))
    ]


# ---------------------------------------------------------------- orchestration

async def localiser(client: Client, demande: Demande, alertes: list[str]) -> tuple[Lieu | None, dict | None]:
    """Point d'analyse : proposition choisie, sinon parcelle saisie, sinon meilleure adresse trouvée."""
    if demande.reference_cadastrale:
        ref = apicarto.lire_reference(demande.reference_cadastrale)
        if ref is None:
            alertes.append("Référence cadastrale illisible (attendu par ex. « 69123 AB 45 ») : elle est ignorée.")
        elif feature := await apicarto.parcelle(client, reference=ref):
            centre = shape(feature["geometry"]).representative_point()
            libelle = demande.libelle or demande.adresse or f"Parcelle {demande.reference_cadastrale}"
            return Lieu(lat=centre.y, lon=centre.x, libelle=libelle, code_insee=ref["code_insee"]), feature
        else:
            alertes.append("Parcelle introuvable au cadastre : l'analyse utilise l'adresse.")
    if demande.lat is not None and demande.lon is not None:
        return Lieu(lat=demande.lat, lon=demande.lon, libelle=demande.libelle or demande.adresse,
                    code_insee=demande.code_insee), None
    if not demande.adresse.strip():
        alertes.append("Saisir une adresse ou une référence cadastrale.")
        return None, None
    lieux = await geocodage.rechercher(client, demande.adresse, limite=1)
    if not lieux:
        alertes.append("Adresse introuvable, ou service de géocodage indisponible.")
        return None, None
    lieu = lieux[0]
    if (lieu.score or 0) < SCORE_GEOCODAGE_MIN or lieu.type != "housenumber":
        alertes.append(f"Adresse approximative (trouvée : « {lieu.libelle} », précision {lieu.type or 'inconnue'}) : "
                       "vérifier le point sur le schéma.")
    return lieu, None


async def analyser(client: Client, demande: Demande) -> Analyse:
    analyse = Analyse(demande=demande)
    lieu, parcelle = await localiser(client, demande, analyse.alertes)
    if lieu is None:
        analyse.sources = client.sources
        return analyse
    repere = Repere(lieu.lat, lieu.lon)
    collectes = [osm.elements(client, repere), georisques.interroger(client, lieu),
                 apicarto.zones_nature(client, repere.cercle(500)), apicarto.urbanisme(client, lieu)]
    if parcelle is None:
        collectes.append(apicarto.parcelle(client, lieu=lieu))
    elements, risques, nature, (zones, sup), *reste = await asyncio.gather(*collectes)
    parcelle = parcelle or (reste[0] if reste else None)
    if not lieu.code_insee and parcelle:
        lieu.code_insee = str(parcelle.get("properties", {}).get("code_insee", ""))
    donnees = Donnees(lieu=lieu, parcelle=parcelle, osm=elements, risques=risques, nature=nature,
                      zones_urba=zones, servitudes=sup)
    analyse.lieu, analyse.parcelle = lieu, parcelle
    analyse.elements = elements or []
    analyse.exigences = exigences(donnees, demande.type_projet)
    analyse.sources = client.sources
    if any(not s.ok for s in client.sources):
        analyse.alertes.append("Certaines sources n'ont pas répondu : les lignes concernées sont marquées "
                               "« Source indisponible ». Relancer l'analyse plus tard.")
    return analyse

