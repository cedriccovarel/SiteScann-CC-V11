"""API Carto de l'IGN : cadastre, espaces naturels (Natura 2000, ZNIEFF) et Géoportail de l'Urbanisme."""
import asyncio
import json
import re

from shapely.geometry import mapping

from app.config import APICARTO_URL
from app.http import Client
from app.models import Lieu
from app.sources import nom_de

NATURE = {
    "natura-habitat": "Natura 2000 – directive Habitats",
    "natura-oiseaux": "Natura 2000 – directive Oiseaux",
    "znieff1": "ZNIEFF de type I",
    "znieff2": "ZNIEFF de type II",
}

# « 69123 AB 45 », « 69123 000 AB 0045 », « 2A004 B 12 »
_REFERENCE = re.compile(r"^\s*(\d[\dAB]\d{3})\s*(?:(\d{3})\s*)?([A-Z0-9]{1,2})\s*(\d{1,4})\s*$", re.I)


def lire_reference(reference: str) -> dict | None:
    m = _REFERENCE.match(reference or "")
    if not m:
        return None
    insee, prefixe, section, numero = m.groups()
    params = {"code_insee": insee.upper(), "section": section.upper().rjust(2, "0"), "numero": numero.rjust(4, "0")}
    if prefixe:
        params["com_abs"] = prefixe
    return params


def _point(lieu: Lieu) -> str:
    return json.dumps({"type": "Point", "coordinates": [lieu.lon, lieu.lat]})


def _features(payload) -> list[dict] | None:
    if isinstance(payload, dict) and isinstance(payload.get("features"), list):
        return payload["features"]
    return None


async def parcelle(client: Client, *, lieu: Lieu | None = None, reference: dict | None = None) -> dict | None:
    """Parcelle cadastrale (Feature GeoJSON) par référence ou sous le point."""
    params = reference or {"geom": _point(lieu)}
    features = _features(await client.json("Cadastre (API Carto IGN)", f"{APICARTO_URL}/cadastre/parcelle", params))
    return features[0] if features else None


async def zones_nature(client: Client, zone_geom) -> dict[str, list[str] | None]:
    """Noms des zones intersectant la zone d'étude, par type (None si la source n'a pas répondu)."""
    geom = json.dumps(mapping(zone_geom))
    reponses = await asyncio.gather(*(
        client.json(f"{libelle} (API Carto IGN)", f"{APICARTO_URL}/nature/{cle}", {"geom": geom})
        for cle, libelle in NATURE.items()
    ))
    resultat = {}
    for cle, payload in zip(NATURE, reponses):
        features = _features(payload)
        resultat[cle] = None if features is None else sorted({nom_de(f.get("properties")) or "sans nom" for f in features})
    return resultat


async def urbanisme(client: Client, lieu: Lieu) -> tuple[list[dict] | None, list[dict] | None]:
    """Zones du document d'urbanisme et servitudes d'utilité publique (surfaciques) au point."""
    geom = _point(lieu)
    zones, sup = await asyncio.gather(
        client.json("Géoportail de l'Urbanisme – zonage", f"{APICARTO_URL}/gpu/zone-urba", {"geom": geom}),
        client.json("Géoportail de l'Urbanisme – servitudes", f"{APICARTO_URL}/gpu/assiette-sup-s", {"geom": geom}),
    )
    return (
        None if _features(zones) is None else [f.get("properties", {}) for f in _features(zones)],
        None if _features(sup) is None else [f.get("properties", {}) for f in _features(sup)],
    )
