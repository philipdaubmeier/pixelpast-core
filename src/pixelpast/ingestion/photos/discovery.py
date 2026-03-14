"""Discovery-facing photo ingestion contracts."""

from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
)

__all__ = [
    "PhotoAssetCandidate",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
]
