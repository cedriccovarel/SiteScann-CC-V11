"""Géocodage d'adresse (service de la Géoplateforme IGN, données BAN)."""
from app.config import GEOCODAGE_URL
from app.http import Client
from app.models import Lieu

SOURCE = "Géocodage (Géoplateforme IGN / BAN)"


async def rechercher(client: Client, texte: str, limite: int = 5) -> list[Lieu]:
    payload = await client.json(SOURCE, GEOCODAGE_URL, {"q": texte, "limit": limite})
    lieux = []
    for f in (payload or {}).get("features", []):
        lon, lat = f["geometry"]["coordinates"]
        p = f.get("properties", {})
        lieux.append(Lieu(lat=lat, lon=lon, libelle=p.get("label", ""), code_insee=p.get("citycode", ""),
                          score=p.get("score"), type=p.get("type", "")))
    return lieux
