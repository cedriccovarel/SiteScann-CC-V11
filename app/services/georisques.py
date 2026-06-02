import os
import httpx

BASE = os.getenv("GEORISQUES_API_BASE", "https://www.georisques.gouv.fr/api/v1")

# Endpoints can evolve. V1.1 keeps best-effort raw responses and then normalises what is readable.
CANDIDATES = [
    ("rapport_risque", "/resultats_rapport_risque", "latlon"),
    ("argiles", "/rga", "latlon"),
    ("radon", "/radon", "latlon"),
    ("sismicite", "/zonage_sismique", "latlon"),
    ("mouvements_terrain", "/mouvements_terrain", "latlon"),
    ("cavites", "/cavites", "latlon"),
    ("installations_classees", "/installations_classees", "latlon"),
]

async def fetch_georisques(lat: float, lon: float) -> dict:
    out = {"source": "Georisques", "items": {}, "errors": []}
    async with httpx.AsyncClient(timeout=35, headers={"User-Agent": "SiteScan-PRESTATERRE/1.1"}) as client:
        for key, path, mode in CANDIDATES:
            params = {"latlon": f"{lon},{lat}"} if mode == "latlon" else {}
            url = f"{BASE}{path}"
            try:
                r = await client.get(url, params=params)
                if r.status_code >= 400:
                    out["errors"].append({"endpoint": key, "status": r.status_code, "detail": r.text[:300]})
                    continue
                out["items"][key] = r.json()
            except Exception as exc:
                out["errors"].append({"endpoint": key, "detail": str(exc)})
    return out
