"""Photo ingestion connector package."""

from pixelpast.ingestion.photos.connector import PhotoConnector, PhotoExifMetadata
from pixelpast.ingestion.photos.contracts import (
    PhotoAssetCandidate,
    PhotoDiscoveryError,
    PhotoDiscoveryResult,
    PhotoIngestionProgressSnapshot,
    PhotoIngestionResult,
    PhotoMetadataBatchProgress,
    PhotoPersonCandidate,
)
from pixelpast.ingestion.photos.lifecycle import (
    PhotoIngestionRunCoordinator,
)
from pixelpast.ingestion.photos.service import PhotoIngestionService

__all__ = [
    "PhotoAssetCandidate",
    "PhotoConnector",
    "PhotoDiscoveryError",
    "PhotoDiscoveryResult",
    "PhotoExifMetadata",
    "PhotoIngestionRunCoordinator",
    "PhotoIngestionProgressSnapshot",
    "PhotoIngestionResult",
    "PhotoIngestionService",
    "PhotoMetadataBatchProgress",
    "PhotoPersonCandidate",
]
