from shapely.geometry import LineString

from app.sources import apicarto, georisques, osm
from tests.faux_services import OVERPASS, R, deg


def test_distance_au_point_le_plus_proche_et_non_au_centre():
    route = LineString([(deg(60, -200)["lon"], deg(60, -200)["lat"]), (deg(60, 2000)["lon"], deg(60, 2000)["lat"])])
    distance, _, _ = R.plus_proche(route)
    assert 58 <= distance <= 62


def test_requete_overpass_unique_et_complete():
    q = osm.requete(45.76, 4.835)
    assert q.count("around:") == sum(len(c.filtres) for c in osm.CATEGORIES)
    assert "way.r;out geom;" in q and "rel.r;out tags center;" in q


def test_classement_osm():
    elements = osm.classer(OVERPASS, R)
    par_cat = {}
    for e in elements:
        par_cat.setdefault(e.categorie, []).append(e)
    assert [e.distance_m for e in par_cat["transport_commun"]] == [120]          # doublon fusionné
    assert "enseignement" not in par_cat                                        # école à 1,5 km : hors rayon
    assert par_cat["route"][0].distance_m == 60 and par_cat["route"][0].geometrie["type"] == "LineString"
    assert par_cat["decheterie"][0].distance_m == 2500                          # rayon 3 km
    assert par_cat["apport_volontaire"][0].distance_m == 200
    assert par_cat["pharmacie"][0].nom == "Pharmacie du Centre"
    assert par_cat["protection"][0].distance_m == 450                           # relation : centre
    assert par_cat["industrie"][0].geometrie["type"] == "Polygon"


def test_georisques_ne_devine_jamais():
    # Réponse au format inattendu : signalée, pas interprétée
    assert georisques.lire_sismicite({"message": "zone 5 fort"}).statut == "indisponible"
    assert georisques.lire_sismicite(None).resultat == "Service indisponible"
    # Aucun recensement : réponse officielle explicite
    ligne = georisques.lire_recensement("cavites", {"results": 0, "data": []})
    assert (ligne.statut, ligne.resultat) == ("donnee", "Aucun recensé dans ce rayon")
    ligne = georisques.lire_recensement("icpe", {"results": 7, "data": [{"raisonSociale": "A"}, {"raisonSociale": "B"}]})
    assert ligne.resultat == "7 recensé(s) : A, B …"
    assert georisques.lire_rga({"exposition": "Exposition forte"}).resultat == "Exposition forte"


def test_reference_cadastrale():
    assert apicarto.lire_reference("69123 AB 45") == {"code_insee": "69123", "section": "AB", "numero": "0045"}
    assert apicarto.lire_reference("2a004 000 b 12") == {"code_insee": "2A004", "section": "0B", "numero": "0012",
                                                         "com_abs": "000"}
    assert apicarto.lire_reference("rue de la Paix") is None
