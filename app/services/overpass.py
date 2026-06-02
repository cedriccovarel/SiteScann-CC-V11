import os
import math
import httpx
from app.models import Amenity, LinearFeature

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")

CATEGORY_QUERIES = {
    "ecoles": [
        'node["amenity"~"school|kindergarten|college|university"]',
        'way["amenity"~"school|kindergarten|college|university"]',
    ],
    "transports": [
        'node["public_transport"="platform"]',
        'node["highway"="bus_stop"]',
        'node["railway"~"station|halt|tram_stop|subway_entrance"]',
        'way["railway"~"station|halt|tram_stop|subway_entrance"]',
    ],
    "commerces": [
        'node["shop"~"supermarket|convenience|bakery|butcher|greengrocer|mall|department_store"]',
        'way["shop"~"supermarket|convenience|bakery|butcher|greengrocer|mall|department_store"]',
    ],
    "sante": [
        'node["amenity"~"pharmacy|doctors|clinic|hospital|dentist"]',
        'way["amenity"~"pharmacy|doctors|clinic|hospital|dentist"]',
    ],
    "loisirs_espaces_verts": [
        'node["leisure"~"park|playground|sports_centre|garden"]',
        'way["leisure"~"park|playground|sports_centre|garden"]',
        'way["landuse"~"forest|grass|recreation_ground"]',
        'way["natural"~"wood|water"]',
    ],
    "nuisances_potentielles": [
        'node["man_made"~"works|wastewater_plant"]',
        'way["landuse"~"industrial|quarry|landfill"]',
        'node["amenity"~"fuel|recycling|waste_disposal"]',
    ],
}

WASTE_QUERIES = [
    'node["amenity"="recycling"]', 'way["amenity"="recycling"]',
    'node["recycling_type"]', 'way["recycling_type"]',
    'node["amenity"="waste_disposal"]', 'way["amenity"="waste_disposal"]',
    'node["amenity"="waste_transfer_station"]', 'way["amenity"="waste_transfer_station"]',
]

NOISE_QUERIES = [
    'way["highway"~"motorway|trunk|primary|secondary|tertiary"]',
    'way["railway"~"rail|tram|subway|light_rail"]',
    'way["landuse"~"industrial|quarry|landfill"]',
    'node["aeroway"~"aerodrome|helipad"]',
    'way["aeroway"~"aerodrome|runway|taxiway"]',
]

ACCESS_QUERIES = [
    'way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|service|living_street"]',
    'node["barrier"]',
]

PROTECTED_QUERIES = [
    'way["boundary"="protected_area"]',
    'relation["boundary"="protected_area"]',
    'way["heritage"]',
    'relation["heritage"]',
    'node["historic"]',
    'way["historic"]',
    'relation["historic"]',
    'way["leisure"="nature_reserve"]',
    'relation["leisure"="nature_reserve"]',
]

LANDSCAPE_QUERIES = [
    'way["natural"~"water|wood|tree_row|wetland|scrub"]',
    'way["waterway"]',
    'node["natural"="tree"]',
    'way["leisure"~"park|garden"]',
    'way["landuse"~"forest|orchard|vineyard|meadow|grass"]',
]

def distance_m(lat1, lon1, lat2, lon2):
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _build_query(lat: float, lon: float, radius_m: int, parts: list[str], limit: int = 100) -> str:
    body = "\n".join(f"  {part}(around:{radius_m},{lat},{lon});" for part in parts)
    return f"""
[out:json][timeout:30];
(
{body}
);
out center {limit};
"""

async def _post_overpass(query: str) -> dict:
    headers = {"User-Agent": "SiteScan-PRESTATERRE/1.1", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=50) as client:
        r = await client.post(OVERPASS_URL, data={"data": query}, headers=headers)
        r.raise_for_status()
        return r.json()

def _element_center(el: dict) -> tuple[float | None, float | None]:
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    return lat, lon

def _name(tags: dict) -> str:
    return tags.get("name") or tags.get("brand") or tags.get("operator") or tags.get("ref") or "Non nomme"

async def fetch_category(lat: float, lon: float, radius_m: int, category: str, parts: list[str], limit: int = 30) -> list[Amenity]:
    query = _build_query(lat, lon, radius_m, parts, limit=max(limit, 80))
    data = await _post_overpass(query)
    items: list[Amenity] = []
    seen = set()
    for el in data.get("elements", []):
        item_lat, item_lon = _element_center(el)
        if item_lat is None or item_lon is None:
            continue
        tags = el.get("tags", {})
        key = (round(float(item_lat), 6), round(float(item_lon), 6), _name(tags), category)
        if key in seen:
            continue
        seen.add(key)
        items.append(Amenity(
            category=category,
            name=_name(tags),
            lat=float(item_lat),
            lon=float(item_lon),
            distance_m=round(distance_m(lat, lon, float(item_lat), float(item_lon)), 0),
            source="OpenStreetMap / Overpass",
            tags={k: v for k, v in tags.items() if k in {"amenity", "shop", "highway", "railway", "leisure", "landuse", "natural", "historic", "heritage", "public_transport", "operator"}},
        ))
    items.sort(key=lambda x: x.distance_m or 999999)
    return items[:limit]

async def fetch_amenities(lat: float, lon: float, radius_m: int) -> list[Amenity]:
    results: list[Amenity] = []
    for category, parts in CATEGORY_QUERIES.items():
        try:
            results.extend(await fetch_category(lat, lon, radius_m, category, parts, limit=25))
        except Exception as exc:
            results.append(Amenity(category=category, name=f"Erreur Overpass: {exc}", source="Overpass"))
    return results

async def fetch_waste_sites(lat: float, lon: float, radius_m: int) -> list[Amenity]:
    try:
        return await fetch_category(lat, lon, radius_m, "dechets", WASTE_QUERIES, limit=60)
    except Exception as exc:
        return [Amenity(category="dechets", name=f"Erreur Overpass dechets: {exc}", source="Overpass")]

async def fetch_noise_features(lat: float, lon: float, radius_m: int = 700) -> list[LinearFeature]:
    query = _build_query(lat, lon, radius_m, NOISE_QUERIES, limit=120)
    data = await _post_overpass(query)
    features: list[LinearFeature] = []
    for el in data.get("elements", []):
        item_lat, item_lon = _element_center(el)
        if item_lat is None or item_lon is None:
            continue
        tags = el.get("tags", {})
        cat = "route" if "highway" in tags else "rail" if "railway" in tags else "industrie/aerien"
        features.append(LinearFeature(
            category=cat,
            name=_name(tags),
            lat=float(item_lat),
            lon=float(item_lon),
            distance_m=round(distance_m(lat, lon, float(item_lat), float(item_lon)), 0),
            source="OpenStreetMap / Overpass",
            tags={k: v for k, v in tags.items() if k in {"highway", "railway", "landuse", "aeroway", "name", "ref"}},
        ))
    features.sort(key=lambda x: x.distance_m or 999999)
    return features[:60]

async def fetch_access_features(lat: float, lon: float, radius_m: int = 500) -> list[Amenity]:
    return await fetch_category(lat, lon, radius_m, "voies_acces", ACCESS_QUERIES, limit=40)

async def fetch_protected_features(lat: float, lon: float, radius_m: int = 1000) -> list[Amenity]:
    return await fetch_category(lat, lon, radius_m, "zones_protegees_patrimoine_osm", PROTECTED_QUERIES, limit=50)

async def fetch_landscape_features(lat: float, lon: float, radius_m: int = 500) -> list[Amenity]:
    return await fetch_category(lat, lon, radius_m, "paysage_eau_vegetal", LANDSCAPE_QUERIES, limit=50)
