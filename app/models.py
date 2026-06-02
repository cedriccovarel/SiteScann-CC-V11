from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SiteRequest(BaseModel):
    address: Optional[str] = Field(default=None, description="Adresse complete")
    cadastral_reference: Optional[str] = Field(default=None, description="Reference cadastrale libre")
    radius_m: int = Field(default=500, ge=100, le=2000)
    waste_radius_m: int = Field(default=3000, ge=500, le=10000)
    building_type: str = Field(default="logement", description="logement, tertiaire, mixte")
    surface_m2: Optional[float] = Field(default=None, ge=0)

class GeoPoint(BaseModel):
    lat: float
    lon: float
    label: str | None = None
    score: float | None = None
    city: str | None = None
    postcode: str | None = None
    citycode: str | None = None

class Amenity(BaseModel):
    category: str
    name: str
    distance_m: float | None = None
    lat: float | None = None
    lon: float | None = None
    source: str = "OpenStreetMap / Overpass"
    tags: Dict[str, Any] = Field(default_factory=dict)

class LinearFeature(BaseModel):
    category: str
    name: str
    distance_m: float | None = None
    lat: float | None = None
    lon: float | None = None
    source: str = "OpenStreetMap / Overpass"
    tags: Dict[str, Any] = Field(default_factory=dict)

class RiskItem(BaseModel):
    theme: str
    presence: str = "Non determine"
    level: str = "A verifier"
    comment: str = ""
    source: str = ""
    raw_key: str | None = None

class SiteAnalysis(BaseModel):
    input: SiteRequest
    point: Optional[GeoPoint] = None
    parcel: Dict[str, Any] = Field(default_factory=dict)
    risks: Dict[str, Any] = Field(default_factory=dict)
    risk_items: List[RiskItem] = Field(default_factory=list)
    amenities: List[Amenity] = Field(default_factory=list)
    waste_sites: List[Amenity] = Field(default_factory=list)
    transport_features: List[Amenity] = Field(default_factory=list)
    noise_features: List[LinearFeature] = Field(default_factory=list)
    noise: Dict[str, Any] = Field(default_factory=dict)
    mobility: Dict[str, Any] = Field(default_factory=dict)
    protected_areas: Dict[str, Any] = Field(default_factory=dict)
    geology: Dict[str, Any] = Field(default_factory=dict)
    water: Dict[str, Any] = Field(default_factory=dict)
    planning: Dict[str, Any] = Field(default_factory=dict)
    landscape: Dict[str, Any] = Field(default_factory=dict)
    map_layers: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
