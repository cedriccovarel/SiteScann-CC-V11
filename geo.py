"""Calculs géométriques en mètres autour du site (projection locale)."""
import math

import numpy as np
import shapely
from shapely.geometry import Point, mapping
from shapely.ops import nearest_points

M_PAR_DEG_LAT = 110_574


class Repere:
    """Projection équirectangulaire centrée sur le site : écart de quelques mètres au plus dans un rayon de 5 km."""

    def __init__(self, lat: float, lon: float):
        self.lat0, self.lon0 = lat, lon
        self.kx = 111_320 * math.cos(math.radians(lat))

    def vers_m(self, lon, lat):
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * M_PAR_DEG_LAT

    def vers_deg(self, x, y):
        return self.lon0 + x / self.kx, self.lat0 + y / M_PAR_DEG_LAT

    def en_metres(self, geom_deg):
        return shapely.transform(geom_deg, lambda c: np.column_stack(self.vers_m(c[:, 0], c[:, 1])))

    def en_degres(self, geom_m):
        return shapely.transform(geom_m, lambda c: np.column_stack(self.vers_deg(c[:, 0], c[:, 1])))

    def plus_proche(self, geom_deg) -> tuple[int, float, float]:
        """Distance (m) du site à la géométrie et coordonnées (lat, lon) du point le plus proche."""
        geom_m = self.en_metres(geom_deg)
        origine = Point(0, 0)
        if geom_m.contains(origine):
            return 0, self.lat0, self.lon0
        proche = nearest_points(geom_m, origine)[0]
        lon, lat = self.vers_deg(proche.x, proche.y)
        return round(geom_m.distance(origine)), lat, lon

    def cercle(self, rayon_m: float):
        """Cercle de rayon donné autour du site, en degrés (shapely)."""
        return self.en_degres(Point(0, 0).buffer(rayon_m, 32))

    def pour_carte(self, geom_deg, rayon_max_m: float = 1200, tolerance_m: float = 2) -> dict:
        """Géométrie GeoJSON allégée (découpée au rayon utile et simplifiée) pour l'affichage."""
        geom_m = self.en_metres(geom_deg).intersection(Point(0, 0).buffer(rayon_max_m, 32))
        return mapping(self.en_degres(geom_m.simplify(tolerance_m)))
