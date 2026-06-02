from app.models import RiskItem

THEMES = [
    "Inondation",
    "Retrait-gonflement des argiles",
    "Radon",
    "Sismicite",
    "Mouvements de terrain",
    "Cavites souterraines",
    "Installations classees / risques technologiques",
    "Pollution potentielle des sols",
    "PPRN / PPRT / documents de prevention",
]

def _flatten_text(value, max_chars=6000) -> str:
    try:
        txt = str(value)
    except Exception:
        txt = ""
    return txt[:max_chars].lower()

def _level_from_text(txt: str) -> str:
    if any(w in txt for w in ["fort", "eleve", "élevé", "zone 4", "zone 5", "catégorie 3", "categorie 3"]):
        return "Fort"
    if any(w in txt for w in ["moyen", "modere", "modéré", "zone 3", "catégorie 2", "categorie 2"]):
        return "Modere"
    if any(w in txt for w in ["faible", "zone 1", "zone 2", "catégorie 1", "categorie 1"]):
        return "Faible"
    return "A verifier"

def normalise_georisques(raw: dict) -> list[RiskItem]:
    items = raw.get("items", {}) if isinstance(raw, dict) else {}
    all_txt = _flatten_text(items)
    results: list[RiskItem] = []

    mapping = [
        ("rapport_risque", "Inondation", ["inond", "ppri", "submersion"]),
        ("argiles", "Retrait-gonflement des argiles", ["argile", "retrait", "gonflement", "rga"]),
        ("radon", "Radon", ["radon"]),
        ("sismicite", "Sismicite", ["sismi", "zone de sismic"]),
        ("mouvements_terrain", "Mouvements de terrain", ["mouvement", "glissement", "eboulement", "éboulement"]),
        ("cavites", "Cavites souterraines", ["cavite", "cavité", "souterrain"]),
        ("installations_classees", "Installations classees / risques technologiques", ["icpe", "installation", "classee", "classée", "seveso"]),
        ("rapport_risque", "Pollution potentielle des sols", ["pollution", "sis", "basol", "basias"]),
        ("rapport_risque", "PPRN / PPRT / documents de prevention", ["ppr", "plan de prevention", "prévention"]),
    ]

    for key, theme, needles in mapping:
        source_value = items.get(key, {})
        txt = _flatten_text(source_value) or all_txt
        present = any(n in txt for n in needles)
        has_data = bool(source_value)
        if present:
            presence = "Oui / donnees detectees"
            level = _level_from_text(txt)
            comment = "Donnee detectee dans la reponse Georisques. Verification officielle a conserver en annexe avant usage opposable."
        elif has_data:
            presence = "Non identifie dans la reponse"
            level = "Faible ou non determine"
            comment = "Endpoint disponible, aucun signal evident detecte par la maquette. A confirmer sur Georisques."
        else:
            presence = "Non determine"
            level = "A verifier"
            comment = "Endpoint non disponible ou non exploite pour ce theme dans cette execution."
        results.append(RiskItem(theme=theme, presence=presence, level=level, comment=comment, source="Georisques", raw_key=key))
    return results
