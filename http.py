"""Accès aux API externes : un seul client, un cache mémoire et le journal des sources interrogées."""
import time
from typing import Any

import httpx

from app.config import CACHE_TTL_S, TIMEOUT_S, USER_AGENT
from app.models import Source

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_MAX = 2000


def vider_cache() -> None:
    _CACHE.clear()


class Client:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(
            timeout=TIMEOUT_S,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            transport=transport,
            follow_redirects=True,
        )
        self.sources: list[Source] = []

    async def json(self, nom: str, url: str, params: dict | None = None, data: dict | None = None) -> Any:
        """Renvoie la réponse JSON, ou None si la source est indisponible (l'échec est journalisé)."""
        req = self._http.build_request("POST" if data else "GET", url, params=params, data=data)
        cle = f"{req.method} {req.url} {data!r}"
        payload, erreur = None, ""
        cached = _CACHE.get(cle)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_S:
            payload = cached[1]
        else:
            try:
                rep = await self._http.send(req)
                rep.raise_for_status()
                payload = rep.json()
                if len(_CACHE) >= _CACHE_MAX:
                    _CACHE.pop(next(iter(_CACHE)))
                _CACHE[cle] = (time.monotonic(), payload)
            except httpx.HTTPStatusError as exc:
                erreur = f"HTTP {exc.response.status_code}"
            except (httpx.HTTPError, ValueError) as exc:
                erreur = f"{type(exc).__name__}: {exc}"[:200]
        self.sources.append(Source(nom=nom, url=f"{req.url.host}{req.url.path}", ok=not erreur, detail=erreur))
        return payload

    async def aclose(self) -> None:
        await self._http.aclose()
