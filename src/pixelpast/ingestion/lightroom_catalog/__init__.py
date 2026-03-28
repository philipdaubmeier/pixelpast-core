"""Lightroom Classic catalog ingestion contracts and XMP helpers."""

from pixelpast.ingestion.lightroom_catalog.contracts import (
    LightroomAssetCandidate,
    LightroomCatalogCandidate,
    LightroomCatalogDescriptor,
    LightroomChosenImageRow,
    LightroomCollectionMembership,
    LightroomFaceRegion,
    LightroomIngestionResult,
    LightroomPersonCandidate,
    LightroomTransformError,
    LightroomXmpPayload,
)
from pixelpast.ingestion.lightroom_catalog.xmp import (
    decompress_lightroom_xmp_blob,
    parse_lightroom_xmp_payload,
)

__all__ = [
    "decompress_lightroom_xmp_blob",
    "LightroomAssetCandidate",
    "LightroomCatalogCandidate",
    "LightroomCatalogDescriptor",
    "LightroomChosenImageRow",
    "LightroomCollectionMembership",
    "LightroomFaceRegion",
    "LightroomIngestionResult",
    "LightroomPersonCandidate",
    "LightroomTransformError",
    "LightroomXmpPayload",
    "parse_lightroom_xmp_payload",
]
