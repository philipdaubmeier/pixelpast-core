"""Health-style API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Check API process health",
    description=(
        "Return a lightweight liveness payload for the local PixelPast API "
        "process. This endpoint does not verify connector availability or "
        "database contents."
    ),
    response_description="Minimal liveness status for the running API process.",
)
def health() -> dict[str, str]:
    """Return a minimal process health payload."""

    return {"status": "ok"}
