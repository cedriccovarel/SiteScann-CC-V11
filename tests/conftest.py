import pytest
from fastapi.testclient import TestClient

from app.http import Client, vider_cache
from app.main import app, client
from tests import faux_services


@pytest.fixture(autouse=True)
def cache_vide():
    vider_cache()


@pytest.fixture
def web():
    """Application branchée sur les services simulés ; `web.pannes` choisit les services en panne."""
    pannes = {"/api/v1/ssp/casias"}

    async def faux_client():
        c = Client(transport=faux_services.transport(pannes))
        yield c
        await c.aclose()

    app.dependency_overrides[client] = faux_client
    tc = TestClient(app)
    tc.pannes = pannes
    yield tc
    app.dependency_overrides.clear()
