from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Statut = Literal["donnee", "indicatif", "absent", "a_completer", "indisponible"]

STATUTS: dict[str, str] = {
    "donnee": "Donnée officielle",
    "indicatif": "Indicatif (OpenStreetMap)",
    "absent": "Rien trouvé – à vérifier",
    "a_completer": "À compléter",
    "indisponible": "Source indisponible",
}


def maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Demande(BaseModel):
    adresse: str = Field(default="", max_length=300)
    reference_cadastrale: str = Field(default="", max_length=40)
    type_projet: Literal["neuf", "renovation"] = "neuf"
    # Renseignés quand l'utilisateur choisit une proposition du géocodeur.
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    libelle: str = Field(default="", max_length=300)
    code_insee: str = Field(default="", max_length=5)

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _vide_si_absent(cls, v):
        return None if v == "" else v  # champs cachés du formulaire non remplis


class Lieu(BaseModel):
    lat: float
    lon: float
    libelle: str = ""
    code_insee: str = ""
    score: float | None = None
    type: str = ""


class Source(BaseModel):
    nom: str
    url: str
    ok: bool
    detail: str = ""
    date: str = Field(default_factory=maintenant)


class Element(BaseModel):
    """Objet géolocalisé autour du site."""
    categorie: str
    nom: str = ""
    distance_m: int
    lat: float
    lon: float
    geometrie: dict[str, Any] | None = None
    source: str = "OpenStreetMap"


class Ligne(BaseModel):
    libelle: str
    resultat: str
    statut: Statut
    source: str = ""
    elements: list[Element] = Field(default_factory=list)


class Rubrique(BaseModel):
    titre: str
    piece: str | None = None
    schema_site: bool = False
    lignes: list[Ligne]


class Exigence(BaseModel):
    cle: str
    code: str
    titre: str
    referentiel: str
    version: str
    description: str
    rubriques: list[Rubrique]


class Analyse(BaseModel):
    demande: Demande
    date: str = Field(default_factory=maintenant)
    lieu: Lieu | None = None
    parcelle: dict[str, Any] | None = None
    exigences: list[Exigence] = Field(default_factory=list)
    elements: list[Element] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    alertes: list[str] = Field(default_factory=list)
