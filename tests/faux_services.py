"""Réponses simulées des services externes, autour d'un site fictif à Lyon."""
import httpx

from app.geo import Repere

LAT, LON = 45.7600, 4.8350
R = Repere(LAT, LON)


def deg(x: float, y: float) -> dict:
    lon, lat = R.vers_deg(x, y)
    return {"lat": lat, "lon": lon}


def noeud(i, x, y, **tags):
    return {"type": "node", "id": i, **deg(x, y), "tags": tags}


def chemin(i, points, **tags):
    return {"type": "way", "id": i, "geometry": [deg(x, y) for x, y in points], "tags": tags}


OVERPASS = {"elements": [
    noeud(1, 0, 120, highway="bus_stop", name="Bellecour"),
    noeud(2, 10, 140, highway="bus_stop", name="Bellecour"),          # même arrêt, autre quai
    noeud(3, 300, 0, shop="bakery", name="<script>alert(1)</script>"),
    noeud(4, -450, 0, amenity="pharmacy", name="Pharmacie du Centre"),
    noeud(5, 0, -800, amenity="doctors"),
    noeud(6, 1500, 0, amenity="school", name="École trop loin"),
    chemin(7, [(60, -200), (60, 2000)], highway="primary", name="Quai Jules Courmont"),
    chemin(8, [(-2000, 400), (2000, 400)], railway="rail"),
    chemin(9, [(300, 300), (400, 300), (400, 400), (300, 400), (300, 300)], landuse="industrial"),
    chemin(10, [(-2000, -450), (2000, -450)], power="line"),
    noeud(11, 2500, 0, amenity="recycling", recycling_type="centre", name="Déchèterie Lyon 2"),
    noeud(12, 0, 200, amenity="recycling", recycling_type="container"),
    chemin(13, [(-700, -1000), (-700, 1000)], highway="cycleway"),
    {"type": "relation", "id": 14, "center": deg(450, 0), "tags": {"boundary": "protected_area", "name": "Parc"}},
]}

PARCELLE = {"type": "Feature", "properties": {"code_insee": "69382", "section": "AB", "numero": "0045", "contenance": 812},
            "geometry": {"type": "Polygon", "coordinates": [[[LON - 1e-4, LAT - 1e-4], [LON + 1e-4, LAT - 1e-4],
                                                              [LON + 1e-4, LAT + 1e-4], [LON - 1e-4, LAT + 1e-4],
                                                              [LON - 1e-4, LAT - 1e-4]]]}}

AUCUN = {"results": 0, "data": []}
REPONSES = {
    "/geocodage/search": {"features": [{"geometry": {"coordinates": [LON, LAT]}, "properties": {
        "label": "1 Place Bellecour 69002 Lyon", "score": 0.97, "citycode": "69382", "type": "housenumber"}}]},
    "/api/interpreter": OVERPASS,
    "/api/v1/zonage_sismique": {"data": [{"code_zone": "2", "zone_sismicite": "2 - Faible"}]},
    "/api/v1/rga": {"codeExposition": "1", "exposition": "Exposition faible"},
    "/api/v1/radon": {"data": [{"classe_potentiel": "1"}]},
    "/api/v1/gaspar/risques": {"data": [{"risques_detail": [{"libelle_risque_long": "Inondation"},
                                                            {"libelle_risque_long": "Séisme"}]}]},
    "/api/v1/installations_classees": {"results": 1, "data": [{"raisonSociale": "Usine Exemple"}]},
    "/api/v1/cavites": AUCUN, "/api/v1/mvt": AUCUN,
    "/api/v1/ssp/conclusions_sis": AUCUN, "/api/v1/ssp/instructions": AUCUN,
    "/api/cadastre/parcelle": {"type": "FeatureCollection", "features": [PARCELLE]},
    "/api/nature/natura-habitat": {"features": []}, "/api/nature/natura-oiseaux": {"features": []},
    "/api/nature/znieff1": {"features": [{"properties": {"nom": "Rives du Rhône"}}]},
    "/api/nature/znieff2": {"features": []},
    "/api/gpu/zone-urba": {"features": [{"properties": {"libelle": "UA", "libelong": "Zone urbaine centrale"}}]},
    "/api/gpu/assiette-sup-s": {"features": [{"properties": {"suptype": "ac1", "nomsuplitt": "Église Saint-Nizier"}}]},
}


def transport(pannes: set[str] = frozenset({"/api/v1/ssp/casias"})) -> httpx.MockTransport:
    """Services simulés ; les chemins listés dans `pannes` répondent en erreur 503."""
    def repondre(req: httpx.Request) -> httpx.Response:
        if req.url.path in pannes or req.url.path not in REPONSES:
            return httpx.Response(503)
        return httpx.Response(200, json=REPONSES[req.url.path])
    return httpx.MockTransport(repondre)
