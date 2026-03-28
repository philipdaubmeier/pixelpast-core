"""Lightroom Classic catalog ingestion contracts and read helpers."""

from pixelpast.ingestion.lightroom_catalog.connector import LightroomCatalogConnector
from pixelpast.ingestion.lightroom_catalog.contracts import (
    LoadedLightroomCatalog,
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
    LightroomChosenImageRow,
    LightroomCollectionMembership,
    LightroomCollectionRow,
    LightroomFaceRow,
    LightroomFaceRegion,
    LightroomIngestionResult,
    LightroomPersonCandidate,
    LightroomTransformError,
    LightroomXmpPayload,
)
from pixelpast.ingestion.lightroom_catalog.discovery import LightroomCatalogDiscoverer
from pixelpast.ingestion.lightroom_catalog.fetch import (
    LightroomCatalogFetcher,
    LightroomCatalogLoadProgress,
    open_lightroom_catalog_read_only,
)
from pixelpast.ingestion.lightroom_catalog.xmp import (
    decompress_lightroom_xmp_blob,
    parse_lightroom_xmp_payload,
)

__all__ = [
    "decompress_lightroom_xmp_blob",
    "LightroomCatalogConnector",
    "LightroomCatalogDiscoverer",
    "LightroomCatalogFetcher",
    "LightroomCatalogLoadProgress",
    "LoadedLightroomCatalog",
    "LightroomAssetCandidate",
    "LightroomCatalogCandidate",
    "LightroomCatalogDescriptor",
    "LightroomChosenImageRow",
    "LightroomCollectionMembership",
    "LightroomCollectionRow",
    "LightroomFaceRow",
    "LightroomFaceRegion",
    "LightroomIngestionResult",
    "LightroomPersonCandidate",
    "LightroomTransformError",
    "LightroomXmpPayload",
    "open_lightroom_catalog_read_only",
    "parse_lightroom_xmp_payload",
]
