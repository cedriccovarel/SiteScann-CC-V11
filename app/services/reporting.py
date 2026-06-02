from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
import json
from app.models import SiteAnalysis

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)

def make_summary(analysis: SiteAnalysis) -> dict:
    by_cat = {}
    for a in analysis.amenities:
        if a.name.startswith("Erreur"):
            continue
        by_cat.setdefault(a.category, 0)
        by_cat[a.category] += 1
    risk_levels = [r.level for r in analysis.risk_items]
    if any(l == "Fort" for l in risk_levels) or analysis.noise.get("level") == "Fort potentiel de nuisance":
        vigilance = "forte"
    elif analysis.warnings or any(l in {"Modere", "A verifier"} for l in risk_levels):
        vigilance = "a verifier"
    else:
        vigilance = "moderee"
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "version": "1.1",
        "vigilance": vigilance,
        "counts_500m": by_cat,
        "waste_sites_3km": len([w for w in analysis.waste_sites if not w.name.startswith("Erreur")]),
        "mobility_score_100": analysis.mobility.get("score_100"),
        "noise_level": analysis.noise.get("level"),
    }

def to_xml(analysis: SiteAnalysis) -> str:
    point = analysis.point
    coord = f'lat="{point.lat}" lon="{point.lon}"' if point else ""
    amenities = "\n".join(
        f'    <equipement categorie="{escape(a.category)}" nom="{escape(a.name)}" distance_m="{a.distance_m or ""}" source="{escape(a.source)}" />'
        for a in analysis.amenities
    )
    risks = "\n".join(
        f'    <risque theme="{escape(r.theme)}" presence="{escape(r.presence)}" niveau="{escape(r.level)}"><commentaire>{escape(r.comment)}</commentaire></risque>'
        for r in analysis.risk_items
    )
    waste = "\n".join(
        f'    <site_dechets nom="{escape(a.name)}" distance_m="{a.distance_m or ""}" source="{escape(a.source)}" />'
        for a in analysis.waste_sites
    )
    noise = "\n".join(
        f'    <source_bruit categorie="{escape(f.category)}" nom="{escape(f.name)}" distance_m="{f.distance_m or ""}" />'
        for f in analysis.noise_features
    )
    warnings = "\n".join(f"    <alerte>{escape(w)}</alerte>" for w in analysis.warnings)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<analyse_site version="1.1">
  <identification>
    <adresse>{escape(analysis.input.address or "")}</adresse>
    <reference_cadastrale>{escape(analysis.input.cadastral_reference or "")}</reference_cadastrale>
    <type_batiment>{escape(analysis.input.building_type or "")}</type_batiment>
    <surface_m2>{analysis.input.surface_m2 or ""}</surface_m2>
    <coordonnees {coord}/>
  </identification>
  <synthese vigilance="{escape(str(analysis.summary.get('vigilance', '')))}" date="{escape(str(analysis.summary.get('generated_at', '')))}" mobilite_score="{escape(str(analysis.mobility.get('score_100', '')))}" bruit="{escape(str(analysis.noise.get('level', '')))}" />
  <risques>
{risks}
  </risques>
  <mobilite niveau="{escape(str(analysis.mobility.get('level', '')))}" score_100="{escape(str(analysis.mobility.get('score_100', '')))}">
    <commentaire>{escape(str(analysis.mobility.get('comment', '')))}</commentaire>
  </mobilite>
  <bruit niveau="{escape(str(analysis.noise.get('level', '')))}">
{noise}
  </bruit>
  <equipements rayon_m="{analysis.input.radius_m}">
{amenities}
  </equipements>
  <dechets rayon_m="{analysis.input.waste_radius_m}">
{waste}
  </dechets>
  <zones_protegees statut="{escape(str(analysis.protected_areas.get('status', '')))}" niveau="{escape(str(analysis.protected_areas.get('level', '')))}" />
  <sols_geologie statut="{escape(str(analysis.geology.get('status', '')))}"><commentaire>{escape(str(analysis.geology.get('note', '')))}</commentaire></sols_geologie>
  <eaux_souterraines statut="{escape(str(analysis.water.get('status', '')))}"><commentaire>{escape(str(analysis.water.get('note', '')))}</commentaire></eaux_souterraines>
  <urbanisme statut="{escape(str(analysis.planning.get('status', '')))}"><commentaire>{escape(str(analysis.planning.get('note', '')))}</commentaire></urbanisme>
  <alertes>
{warnings}
  </alertes>
</analyse_site>
'''

def save_xml(analysis: SiteAnalysis) -> str:
    filename = f"analyse_site_v11_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    path = REPORT_DIR / filename
    path.write_text(to_xml(analysis), encoding="utf-8")
    return filename

def save_geojson(analysis: SiteAnalysis) -> str:
    filename = f"analyse_site_v11_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
    features = []
    if analysis.point:
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [analysis.point.lon, analysis.point.lat]}, "properties": {"category": "site", "name": analysis.point.label or analysis.input.address}})
    for group_name, objs in analysis.map_layers.items():
        for obj in objs:
            lat, lon = obj.get("lat"), obj.get("lon")
            if lat is None or lon is None:
                continue
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {"layer": group_name, "category": obj.get("category"), "name": obj.get("name"), "distance_m": obj.get("distance_m")}})
    path = REPORT_DIR / filename
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, indent=2), encoding="utf-8")
    return filename
