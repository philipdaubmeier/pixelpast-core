"""Photo ingestion connector package."""

from pixelpast.ingestion.photos.connector import (
    PhotoAssetCandidate,
    PhotoConnector,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoExifMetadata,
    PhotoMetadataBatchProgress,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos.service import (
    PhotoIngestionProgressSnapshot,
    PhotoIngestionResult,
    PhotoIngestionService,
)

__all__ = [
    "PhotoAssetCandidate",
    "PhotoConnector",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoExifMetadata",
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoIngestionService",
    "PhotoMetadataBatchProgress",
    "PhotoPersonCandidate",
]
