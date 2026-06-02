from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.models import SiteRequest, SiteAnalysis
from app.services.geocoding import geocode_address
from app.services.overpass import (
    fetch_amenities,
    fetch_waste_sites,
    fetch_noise_features,
    fetch_access_features,
    fetch_protected_features,
    fetch_landscape_features,
)
from app.services.georisques import fetch_georisques
from app.services.risk_normalizer import normalise_georisques
from app.services.enrichment import (
    mobility_analysis,
    noise_analysis,
    protected_analysis,
    landscape_analysis,
    geology_placeholder,
    water_placeholder,
    planning_placeholder,
)
from app.services.reporting import make_summary, save_xml, save_geojson, REPORT_DIR

app = FastAPI(title="SiteScan PRESTATERRE V1.1", version="1.1.0")
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyse", response_class=HTMLResponse)
async def analyse_form(
    request: Request,
    address: str = Form(default=""),
    cadastral_reference: str = Form(default=""),
    building_type: str = Form(default="logement"),
    surface_m2: str = Form(default=""),
):
    surface = None
    try:
        surface = float(surface_m2.replace(",", ".")) if surface_m2.strip() else None
    except Exception:
        surface = None
    req = SiteRequest(
        address=address.strip() or None,
        cadastral_reference=cadastral_reference.strip() or None,
        building_type=building_type.strip() or "logement",
        surface_m2=surface,
    )
    analysis = await run_analysis(req)
    xml_file = save_xml(analysis)
    geojson_file = save_geojson(analysis)
    return templates.TemplateResponse(
        "report.html",
        {"request": request, "analysis": analysis, "xml_file": xml_file, "geojson_file": geojson_file},
    )

@app.post("/api/analyse")
async def analyse_api(req: SiteRequest):
    return await run_analysis(req)

@app.get("/reports/{filename}")
async def get_report(filename: str):
    path = REPORT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "Rapport introuvable")
    return FileResponse(path)

async def run_analysis(req: SiteRequest) -> SiteAnalysis:
    warnings: list[str] = []
    point = None
    if req.address:
        try:
            point = await geocode_address(req.address)
        except Exception as exc:
            warnings.append(f"Service de geocodage indisponible: {exc}")

    if not point:
        warnings.append("Adresse non geocodee. Verifie l'adresse, ou reessaie si l'API Adresse est temporairement indisponible.")
        analysis = SiteAnalysis(input=req, warnings=warnings)
        analysis.summary = make_summary(analysis)
        return analysis

    amenities = []
    waste = []
    noise_features = []
    access_features = []
    protected_features = []
    landscape_features = []

    try:
        amenities = await fetch_amenities(point.lat, point.lon, req.radius_m)
    except Exception as exc:
        warnings.append(f"Equipements OSM indisponibles: {exc}")

    try:
        access_features = await fetch_access_features(point.lat, point.lon, req.radius_m)
    except Exception as exc:
        warnings.append(f"Voies d'acces OSM indisponibles: {exc}")

    try:
        waste = await fetch_waste_sites(point.lat, point.lon, req.waste_radius_m)
    except Exception as exc:
        warnings.append(f"Collecte dechets indisponible via Overpass: {exc}")

    try:
        noise_features = await fetch_noise_features(point.lat, point.lon, 700)
    except Exception as exc:
        warnings.append(f"Detection bruit/nuisances OSM indisponible: {exc}")

    try:
        protected_features = await fetch_protected_features(point.lat, point.lon, 1200)
    except Exception as exc:
        warnings.append(f"Detection zones protegees/patrimoine OSM indisponible: {exc}")

    try:
        landscape_features = await fetch_landscape_features(point.lat, point.lon, req.radius_m)
    except Exception as exc:
        warnings.append(f"Detection paysage/eau/vegetation OSM indisponible: {exc}")

    try:
        risks = await fetch_georisques(point.lat, point.lon)
        if risks.get("errors"):
            warnings.append("Certains endpoints Georisques n'ont pas repondu. La normalisation V1.1 reste informative.")
    except Exception as exc:
        risks = {"source": "Georisques", "items": {}, "errors": [str(exc)]}
        warnings.append(f"Georisques indisponible: {exc}")

    risk_items = normalise_georisques(risks)
    mobility = mobility_analysis(amenities, point, req)
    noise = noise_analysis(noise_features)
    protected_areas = protected_analysis(protected_features)
    landscape = landscape_analysis(landscape_features)
    geology = geology_placeholder(point)
    water = water_placeholder(point)
    planning = planning_placeholder(point)

    # In the map layer payload, keep only JSON-friendly objects for the template.
    map_layers = {
        "amenities": [a.model_dump() for a in amenities],
        "waste_sites": [a.model_dump() for a in waste[:80]],
        "noise_features": [f.model_dump() for f in noise_features],
        "access_features": [a.model_dump() for a in access_features],
        "protected_features": [a.model_dump() for a in protected_features],
        "landscape_features": [a.model_dump() for a in landscape_features],
    }

    analysis = SiteAnalysis(
        input=req,
        point=point,
        risks=risks,
        risk_items=risk_items,
        amenities=amenities,
        waste_sites=waste,
        transport_features=[a for a in amenities if a.category == "transports"],
        noise_features=noise_features,
        noise=noise,
        mobility=mobility,
        protected_areas=protected_areas,
        geology=geology,
        water=water,
        planning=planning,
        landscape=landscape,
        map_layers=map_layers,
        warnings=warnings,
    )
    analysis.summary = make_summary(analysis)
    return analysis
