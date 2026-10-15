NOMS = ("nom", "name", "sitename", "nom_site", "libelle", "libelong", "nomsuplitt", "nom_etablissement",
        "raisonSociale", "raison_sociale", "nom_usuel", "identifiant", "id")


def nom_de(props: dict | None) -> str:
    """Premier champ « nom » renseigné, quelle que soit la convention de la source."""
    for cle in NOMS:
        valeur = (props or {}).get(cle)
        if valeur not in (None, ""):
            return str(valeur)
    return ""
