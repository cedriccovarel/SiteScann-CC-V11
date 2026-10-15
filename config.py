"""Paramètres modifiables par variables d'environnement."""
import os

GEOCODAGE_URL = os.getenv("GEOCODAGE_URL", "https://data.geopf.fr/geocodage/search")
OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
GEORISQUES_URL = os.getenv("GEORISQUES_URL", "https://www.georisques.gouv.fr/api/v1")
APICARTO_URL = os.getenv("APICARTO_URL", "https://apicarto.ign.fr/api")

TIMEOUT_S = float(os.getenv("SITESCAN_TIMEOUT_S", "40"))
CACHE_TTL_S = int(os.getenv("SITESCAN_CACHE_TTL_S", str(24 * 3600)))
USER_AGENT = "SiteScan-Prestaterre/2.0"

# En dessous de ce score, l'adresse trouvée par le géocodeur est signalée comme incertaine.
SCORE_GEOCODAGE_MIN = 0.6
