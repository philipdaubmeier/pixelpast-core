"""Photo ingestion connector package."""

from pixelpast.ingestion.photos.connector import (
    PhotoAssetCandidate,
    PhotoConnector,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoExifMetadata,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos.service import (
    PhotoIngestionResult,
    PhotoIngestionService,
)

__all__ = [
    "PhotoAssetCandidate",
    "PhotoConnector",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoExifMetadata",
    "PhotoIngestionResult",
    "PhotoIngestionService",
    "PhotoPersonCandidate",
]
