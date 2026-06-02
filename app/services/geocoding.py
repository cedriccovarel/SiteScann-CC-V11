import os
import httpx
from app.models import GeoPoint

API_ADRESSE_URL = os.getenv("API_ADRESSE_URL", "https://api-adresse.data.gouv.fr/search/")

async def geocode_address(address: str) -> GeoPoint | None:
    params = {"q": address, "limit": 1}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(API_ADRESSE_URL, params=params, headers={"User-Agent": "SiteScan-PRESTATERRE/1.1"})
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None
    features = data.get("features", [])
    if not features:
        return None
    feature = features[0]
    lon, lat = feature["geometry"]["coordinates"]
    props = feature.get("properties", {})
    return GeoPoint(
        lat=lat,
        lon=lon,
        label=props.get("label"),
        score=props.get("score"),
        city=props.get("city"),
        postcode=props.get("postcode"),
        citycode=props.get("citycode"),
    )
