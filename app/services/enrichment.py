from collections import Counter
from app.models import Amenity, LinearFeature, SiteRequest, GeoPoint

def count_by_category(items: list[Amenity]) -> dict:
    c = Counter(a.category for a in items if not a.name.startswith("Erreur"))
    return dict(c)

def nearest(items: list[Amenity], category: str) -> float | None:
    distances = [a.distance_m for a in items if a.category == category and a.distance_m is not None and not a.name.startswith("Erreur")]
    return min(distances) if distances else None

def score_from_nearest(distance: float | None, good: int, medium: int) -> int:
    if distance is None:
        return 0
    if distance <= good:
        return 3
    if distance <= medium:
        return 2
    return 1

def mobility_analysis(amenities: list[Amenity], point: GeoPoint, req: SiteRequest) -> dict:
    # Inspired by the Effinergie Ecomobilite logic: location affects likely travel modes.
    # This is not the official Effinergie calculation; it is a project pre-screening indicator.
    n_transport = nearest(amenities, "transports")
    n_commerce = nearest(amenities, "commerces")
    n_ecole = nearest(amenities, "ecoles")
    n_sante = nearest(amenities, "sante")
    score = (
        score_from_nearest(n_transport, 300, 700) * 30
        + score_from_nearest(n_commerce, 400, 900) * 25
        + score_from_nearest(n_ecole, 500, 1000) * 20
        + score_from_nearest(n_sante, 600, 1200) * 15
    )
    # max is 270, normalized to 100.
    score100 = round(min(100, score / 270 * 100), 0)
    if score100 >= 75:
        level = "Fort potentiel d'ecomobilite"
        comment = "Site bien desservi ou proche des services courants. Les modes doux et transports collectifs sont plausibles."
    elif score100 >= 45:
        level = "Potentiel d'ecomobilite moyen"
        comment = "Quelques services ou transports sont accessibles, mais la dependance automobile reste a etudier."
    else:
        level = "Potentiel d'ecomobilite faible ou non documente"
        comment = "Peu de services detectes dans le rayon analyse ou donnees OSM incompletes."
    return {
        "source_inspiration": "Effinergie Ecomobilite - logique de potentiel de mobilite, non calcul officiel",
        "score_100": score100,
        "level": level,
        "comment": comment,
        "nearest": {
            "transport_m": n_transport,
            "commerce_m": n_commerce,
            "ecole_m": n_ecole,
            "sante_m": n_sante,
        },
        "counts": count_by_category(amenities),
    }

def noise_analysis(features: list[LinearFeature]) -> dict:
    nearest_route = min([f.distance_m for f in features if f.category == "route" and f.distance_m is not None], default=None)
    nearest_rail = min([f.distance_m for f in features if f.category == "rail" and f.distance_m is not None], default=None)
    nearest_ind = min([f.distance_m for f in features if f.category == "industrie/aerien" and f.distance_m is not None], default=None)
    warnings = []
    estimated = "Faible ou non determine"
    if nearest_route is not None and nearest_route <= 100:
        warnings.append("Route structurante a moins de 100 m : vigilance acoustique.")
        estimated = "Fort potentiel de nuisance"
    elif nearest_route is not None and nearest_route <= 250:
        warnings.append("Route structurante a moins de 250 m : verifier classement sonore.")
        estimated = "Potentiel de nuisance modere"
    if nearest_rail is not None and nearest_rail <= 300:
        warnings.append("Voie ferree/tram/metro detectee a moins de 300 m : verifier bruit ferroviaire.")
        estimated = "Fort potentiel de nuisance" if nearest_rail <= 150 else ("Potentiel de nuisance modere" if estimated == "Faible ou non determine" else estimated)
    if nearest_ind is not None and nearest_ind <= 500:
        warnings.append("Activite industrielle/aerienne potentielle a proximite : verifier odeurs, poussieres et bruit.")
    return {
        "status": "preanalyse_osm",
        "level": estimated,
        "nearest_route_m": nearest_route,
        "nearest_rail_m": nearest_rail,
        "nearest_industrial_or_air_m": nearest_ind,
        "warnings": warnings,
        "note": "V1.1 : detection indirecte par proximite OSM. Les niveaux dB exigent les cartes strategiques du bruit, PEB et classement sonore officiels.",
        "next_step": "Integrer CBS Lden/Ln, classement sonore routier/ferroviaire et secteurs affectes par le bruit.",
    }

def protected_analysis(features: list[Amenity]) -> dict:
    count = len([f for f in features if not f.name.startswith("Erreur")])
    nearest_m = min([f.distance_m for f in features if f.distance_m is not None and not f.name.startswith("Erreur")], default=None)
    level = "A verifier"
    if count and nearest_m is not None and nearest_m <= 500:
        level = "Vigilance forte"
    elif count:
        level = "Vigilance moderee"
    return {
        "status": "preanalyse_osm_plus_liens_officiels",
        "level": level,
        "count_osm": count,
        "nearest_m": nearest_m,
        "note": "Detection OSM des protections/patrimoine. A completer par INPN/Natura 2000, Atlas des patrimoines, ZNIEFF et TVB/SRADDET.",
        "official_sources_to_check": ["INPN / Natura 2000 / ZNIEFF", "Atlas des patrimoines", "Donnees regionales SRCE/SRADDET TVB"],
    }

def landscape_analysis(features: list[Amenity]) -> dict:
    counts = count_by_category(features)
    nearest_water = min([f.distance_m for f in features if f.tags.get("waterway") or f.tags.get("natural") in {"water", "wetland"} and f.distance_m is not None], default=None)
    return {
        "status": "preanalyse_osm",
        "count_features": len(features),
        "nearest_water_or_wetland_m": nearest_water,
        "note": "Elements paysagers detectes dans le rayon 500 m : eau, vegetation, parcs, boisements. A confirmer par visite de site et orthophoto.",
        "counts": counts,
    }

def geology_placeholder(point: GeoPoint) -> dict:
    return {
        "status": "connecteur_prepare",
        "level": "A completer par couche officielle",
        "note": "BRGM/InfoTerre a integrer par WMS/WFS ou couches prechargees. La maquette prepare la rubrique mais ne conclut pas sur la nature exacte des sols.",
        "official_sources_to_check": ["InfoTerre BRGM", "Carte geologique harmonisee", "Banque du Sous-Sol BSS", "BDLISA / masses d'eau souterraines"],
        "operational_comment": "Prevoir a minima une verification geotechnique G1/G2 selon stade du projet, surtout si argiles, remblais, alluvions, cavites ou nappe potentielle sont signales par les sources officielles.",
    }

def water_placeholder(point: GeoPoint) -> dict:
    return {
        "status": "connecteur_prepare",
        "note": "Masse d'eau souterraine, etat chimique/quantitatif et vulnerabilite a raccorder via SANDRE/Eaufrance/BRGM.",
        "official_sources_to_check": ["SANDRE", "Eaufrance", "Agences de l'eau", "BRGM BDLISA"],
    }

def planning_placeholder(point: GeoPoint) -> dict:
    return {
        "status": "connecteur_prepare",
        "note": "PLU/PLUi, zonage et servitudes a raccorder au Geoportail de l'Urbanisme. Ne pas utiliser cette rubrique comme document opposable en V1.1.",
        "official_sources_to_check": ["Geoportail de l'Urbanisme", "PLU/PLUi communal ou intercommunal", "Servitudes d'utilite publique"],
    }
