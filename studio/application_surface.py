"""Process-level boundaries for the canonical and legacy applications.

The repository still contains one shared FastAPI implementation for backwards
compatibility.  The launch modules wrap that implementation with an explicit
surface boundary so the two applications can run as separate processes while
keeping their routes, databases, and local media stores isolated.
"""

from __future__ import annotations

import os

from starlette.responses import JSONResponse, RedirectResponse


SURFACES = frozenset({"combined", "canonical", "legacy"})
LEGACY_PREFIXES = (
    "/api/v2",
    "/api/photo-studio",
    "/api/orchestrator",
)


def configured_surface() -> str:
    value = os.getenv("STUDIO_APP_SURFACE", "combined").strip().lower()
    return value if value in SURFACES else "combined"


def route_allowed(surface: str, path: str) -> bool:
    """Return whether a request belongs to the selected application surface."""

    if surface == "combined":
        return True
    if surface == "canonical":
        if path == "/":
            return True  # Redirected to the canonical workspace by the wrapper.
        if path == "/generated" or path.startswith("/generated/"):
            return False
        return not any(path == prefix or path.startswith(prefix + "/") for prefix in LEGACY_PREFIXES)
    if surface == "legacy":
        if path in {"/", "/go"} or path.startswith("/go/"):
            return True
        if path == "/static" or path.startswith("/static/"):
            return True
        if path == "/generated" or path.startswith("/generated/"):
            return True
        if path == "/api/health" or path == "/api/models" or path == "/api/monitor" or path == "/api/readiness":
            return True
        return any(path == prefix or path.startswith(prefix + "/") for prefix in LEGACY_PREFIXES)
    return False


class ApplicationSurface:
    """ASGI boundary that exposes only one application surface."""

    def __init__(self, inner, surface: str):
        normalized = surface.strip().lower()
        if normalized not in SURFACES:
            raise ValueError(f"Unsupported application surface: {surface}")
        self.inner = inner
        self.surface = normalized

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.inner(scope, receive, send)
            return

        path = scope.get("path", "") or "/"
        if not route_allowed(self.surface, path):
            response = JSONResponse(
                {
                    "detail": "This route belongs to the other application surface",
                    "application_surface": self.surface,
                },
                status_code=404,
                headers={"X-Studio-App-Surface": self.surface},
            )
            await response(scope, receive, send)
            return

        if self.surface == "canonical" and path == "/":
            response = RedirectResponse("/workspace", status_code=307, headers={"X-Studio-App-Surface": self.surface})
            await response(scope, receive, send)
            return

        async def send_with_surface_header(message):
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-studio-app-surface", self.surface.encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        await self.inner(scope, receive, send_with_surface_header)
