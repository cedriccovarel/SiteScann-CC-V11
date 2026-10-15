"""OpenStreetMap via Overpass : une seule requête, construite à partir de la table des catégories.

La même table sert à écrire la requête et à classer les objets reçus : elle est la seule à modifier
pour ajouter ou ajuster une catégorie.
"""
import re
from dataclasses import dataclass

from shapely.geometry import LineString, Point, Polygon

from app.config import OVERPASS_URL
from app.geo import Repere
from app.http import Client
from app.models import Element

SOURCE = "OpenStreetMap (Overpass)"


@dataclass(frozen=True)
class Categorie:
    cle: str
    libelle: str
    rayon_m: int
    couleur: str
    # Alternatives de filtres ; dans un filtre, toutes les clés doivent correspondre.
    # Valeur "*" : la clé doit exister ; sinon expression régulière sur la valeur entière.
    filtres: tuple[dict[str, str], ...]
    surface: bool = False      # chemin fermé = polygone (sinon ligne)
    voies: bool = False        # objets linéaires seulement (way)


CATEGORIES: tuple[Categorie, ...] = (
    # 1/ Schéma de fonctionnement (500 m)
    Categorie("route", "Route structurante", 500, "#c0392b",
              ({"highway": "(motorway|trunk|primary|secondary|tertiary)(_link)?"},), voies=True),
    Categorie("desserte", "Voie de desserte", 150, "#7f8c8d",
              ({"highway": "residential|living_street|unclassified|service|pedestrian"},), voies=True),
    Categorie("voie_ferree", "Voie ferrée, tram, métro", 500, "#6c3483",
              ({"railway": "rail|light_rail|tram|subway|narrow_gauge"},), voies=True),
    Categorie("eau", "Eau, zone humide", 500, "#2e86c1",
              ({"natural": "water|wetland"}, {"waterway": "river|stream|canal"}), surface=True),
    Categorie("vegetation", "Végétation, parc", 500, "#27ae60",
              ({"leisure": "park|garden"}, {"landuse": "forest|meadow|orchard|vineyard|grass"},
               {"natural": "wood|scrub|tree_row"}), surface=True),
    Categorie("protection", "Espace naturel protégé (OSM)", 500, "#117a65",
              ({"boundary": "protected_area"}, {"leisure": "nature_reserve"}), surface=True),
    # 2/ Contraintes (500 m, 3 km pour les aérodromes)
    Categorie("aerodrome", "Aérodrome, piste", 3000, "#34495e", ({"aeroway": "aerodrome|runway"},), surface=True),
    Categorie("industrie", "Zone industrielle, carrière, station d'épuration", 500, "#a04000",
              ({"landuse": "industrial|quarry|landfill"}, {"man_made": "works|wastewater_plant"}), surface=True),
    Categorie("agricole", "Exploitation agricole", 500, "#b7950b",
              ({"landuse": "farmyard"}, {"building": "farm_auxiliary|cowshed|stable|sty"}), surface=True),
    Categorie("publicite", "Panneau publicitaire", 500, "#d35400", ({"advertising": "billboard|poster_box|column"},)),
    Categorie("electromagnetique", "Ligne haute tension, poste, antenne", 500, "#17202a",
              ({"power": "line|substation"}, {"tower:type": "communication"},
               {"communication:mobile_phone": "yes"}), surface=True),
    Categorie("patrimoine", "Patrimoine, monument (OSM)", 500, "#935116",
              ({"heritage": "*"}, {"historic": "monument|castle|church|manor|archaeological_site|city_gate|ruins"})),
    # 3/ Commerces, services, transports (1 km)
    Categorie("commerce_alimentaire", "Commerce alimentaire", 1000, "#e67e22",
              ({"shop": "supermarket|convenience|bakery|pastry|butcher|greengrocer|deli|cheese|seafood|general|farm"},
               {"amenity": "marketplace"})),
    Categorie("transport_commun", "Transport en commun", 1000, "#1f618d",
              ({"highway": "bus_stop"}, {"amenity": "bus_station"},
               {"railway": "station|halt|tram_stop|subway_entrance"}, {"public_transport": "station"})),
    Categorie("pharmacie", "Pharmacie", 1000, "#e84393", ({"amenity": "pharmacy"}, {"healthcare": "pharmacy"})),
    Categorie("soins", "Médecin, centre de santé", 1000, "#cb4335",
              ({"amenity": "doctors|clinic|hospital|dentist"}, {"healthcare": "doctor|centre|clinic|hospital"})),
    Categorie("enseignement", "École, crèche", 1000, "#2874a6",
              ({"amenity": "school|kindergarten|childcare|college"},)),
    Categorie("piste_cyclable", "Aménagement cyclable", 1000, "#16a085",
              ({"highway": "cycleway"}, {"cycleway": "lane|track|share_busway"},
               {"cycleway:both": "lane|track"}, {"cycleway:right": "lane|track"}, {"cycleway:left": "lane|track"},
               {"bicycle_road": "yes"}), voies=True),
    # 4/ Déchets (compost et apport volontaire avant les déchèteries : premier filtre trouvé = catégorie)
    Categorie("compost", "Compostage partagé", 500, "#6e2c00",
              ({"amenity": "recycling", "recycling:organic": "yes"}, {"amenity": "compost"})),
    Categorie("apport_volontaire", "Point d'apport volontaire", 500, "#45b39d",
              ({"amenity": "recycling", "recycling_type": "container"},)),
    Categorie("decheterie", "Déchèterie, centre de tri ou de traitement", 3000, "#5d6d7e",
              ({"amenity": "recycling", "recycling_type": "centre"}, {"amenity": "waste_transfer_station"},
               {"landuse": "landfill"}), surface=True),
)
PAR_CLE = {c.cle: c for c in CATEGORIES}
LIMITE_PAR_CATEGORIE = 40


def _selecteur(filtre: dict[str, str]) -> str:
    return "".join(f'["{k}"]' if v == "*" else f'["{k}"~"^({v})$"]' for k, v in filtre.items())


def requete(lat: float, lon: float) -> str:
    lignes = [
        f"  {'way' if c.voies else 'nwr'}{_selecteur(f)}(around:{c.rayon_m},{lat:.6f},{lon:.6f});"
        for c in CATEGORIES for f in c.filtres
    ]
    # Géométrie complète pour les points et les chemins ; centre seulement pour les relations (souvent très grandes).
    return "[out:json][timeout:90];\n(\n" + "\n".join(lignes) + "\n)->.r;\nnode.r;out geom;\nway.r;out geom;\nrel.r;out tags center;"


def _correspond(filtre: dict[str, str], tags: dict) -> bool:
    return all(k in tags and (v == "*" or re.fullmatch(v, str(tags[k]))) for k, v in filtre.items())


def categories_de(el: dict) -> list[Categorie]:
    tags = el.get("tags", {})
    return [c for c in CATEGORIES
            if (el.get("type") == "way" or not c.voies) and any(_correspond(f, tags) for f in c.filtres)]


def _geometrie(el: dict, surface: bool):
    if el.get("type") == "node":
        return Point(el["lon"], el["lat"])
    if el.get("geometry"):
        coords = [(p["lon"], p["lat"]) for p in el["geometry"] if p]
        if surface and len(coords) >= 4 and coords[0] == coords[-1]:
            return Polygon(coords).buffer(0)
        return LineString(coords) if len(coords) >= 2 else Point(coords[0])
    centre = el.get("center")
    return Point(centre["lon"], centre["lat"]) if centre else None


def classer(payload: dict, repere: Repere) -> list[Element]:
    """Transforme la réponse Overpass en éléments classés, mesurés jusqu'au point le plus proche."""
    retenus: dict[tuple, Element] = {}
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        nom = tags.get("name") or tags.get("brand") or tags.get("ref") or ""
        for cat in categories_de(el):
            geom = _geometrie(el, cat.surface)
            if geom is None or geom.is_empty:
                break
            distance, lat, lon = repere.plus_proche(geom)
            if distance > cat.rayon_m:
                continue  # hors du rayon de cette catégorie : essayer la suivante
            element = Element(categorie=cat.cle, nom=nom, distance_m=distance, lat=lat, lon=lon, source=SOURCE,
                              geometrie=None if geom.geom_type == "Point" else repere.pour_carte(geom))
            # Un nom identique dans la même catégorie (arrêts de bus de part et d'autre de la rue,
            # tronçons d'une même route) n'est gardé qu'une fois, au plus près.
            cle = (cat.cle, nom) if nom else (cat.cle, el.get("type"), el.get("id"))
            if cle not in retenus or distance < retenus[cle].distance_m:
                retenus[cle] = element
            break
    par_categorie: dict[str, list[Element]] = {}
    for e in sorted(retenus.values(), key=lambda e: e.distance_m):
        par_categorie.setdefault(e.categorie, []).append(e)
    return [e for liste in par_categorie.values() for e in liste[:LIMITE_PAR_CATEGORIE]]


async def elements(client: Client, repere: Repere) -> list[Element] | None:
    """Éléments OSM autour du site, ou None si Overpass n'a pas répondu."""
    payload = await client.json(SOURCE, OVERPASS_URL, data={"data": requete(repere.lat0, repere.lon0)})
    return None if payload is None else classer(payload, repere)
