from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.analyse import analyser
from app.http import Client
from app.models import STATUTS, Analyse, Demande, Lieu
from app.sources import geocodage
from app.sources.osm import CATEGORIES

ICI = Path(__file__).parent
app = FastAPI(title="SiteScan Prestaterre", version="2.0.0")
app.mount("/static", StaticFiles(directory=ICI / "static"), name="static")
templates = Jinja2Templates(directory=ICI / "templates")
templates.env.globals.update(
    STATUTS=STATUTS,
    LEGENDE={c.cle: {"libelle": c.libelle, "couleur": c.couleur} for c in CATEGORIES},
)


async def client():
    c = Client()
    try:
        yield c
    finally:
        await c.aclose()


ClientDep = Annotated[Client, Depends(client)]


@app.get("/", response_class=HTMLResponse)
async def accueil(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/adresses")
async def adresses(c: ClientDep, q: str = Query(min_length=3, max_length=200)) -> list[Lieu]:
    return await geocodage.rechercher(c, q)


@app.post("/api/analyse")
async def analyse_json(demande: Demande, c: ClientDep) -> Analyse:
    return await analyser(c, demande)


@app.post("/analyse", response_class=HTMLResponse)
async def analyse_html(request: Request, demande: Annotated[Demande, Form()], c: ClientDep):
    analyse = await analyser(c, demande)
    return templates.TemplateResponse(request, "rapport.html", {"a": analyse, "donnees": analyse.model_dump(mode="json")})
