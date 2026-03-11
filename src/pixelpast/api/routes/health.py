"""Health-style API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a minimal process health payload."""

    return {"status": "ok"}
