"""Extrait du catalogue d'exigences de l'Observatoire les exigences BEE utiles à l'analyse de site.

Usage : python scripts/extraire_referentiel.py chemin/vers/requirements_catalog.json
Le fichier produit (app/referentiel/bee.json) est la seule source des textes et seuils affichés.
"""
import json
import sys
from pathlib import Path

# Les codes diffèrent entre Neuf et Rénovation : on repère les exigences par leur titre.
TITLES = {
    "Analyse de site": "analyse_site",
    "Potentiel d’éco-mobilité": "eco_mobilite",
    "Acoustique extérieure avant travaux": "acoustique_avant_travaux",
    "Traitement collectif des déchets ménagers": "dechets_menagers",
    "Proximité des modes doux": "modes_doux",
    "Localisation du site et aménagement de ses abords": "localisation_seniors",
}
KEYS = ["referential", "version", "code", "title", "theme", "description", "pieces"]


def main(catalog_path: str) -> None:
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for req in catalog:
        key = TITLES.get(req.get("title", "").strip())
        if key and req.get("referential", "").startswith("BEE Logement"):
            kind = "renovation" if "Rénovation" in req["referential"] else "neuf"
            out.setdefault(kind, {})[key] = {k: req.get(k) for k in KEYS}
    target = Path(__file__).resolve().parent.parent / "app" / "referentiel" / "bee.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{target} : " + ", ".join(f"{k} {sorted(v)}" for k, v in out.items()))


if __name__ == "__main__":
    main(sys.argv[1])
