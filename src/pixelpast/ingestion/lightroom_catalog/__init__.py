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
from pixelpast.ingestion.lightroom_catalog.lifecycle import (
    LIGHTROOM_CATALOG_INITIAL_PHASE,
    LIGHTROOM_CATALOG_JOB_NAME,
    LIGHTROOM_CATALOG_JOB_TYPE,
    LIGHTROOM_CATALOG_MODE,
    LIGHTROOM_CATALOG_SOURCE_TYPE,
    LightroomCatalogIngestionRunCoordinator,
    build_lightroom_catalog_source_external_id,
    build_lightroom_catalog_source_name,
)
from pixelpast.ingestion.lightroom_catalog.persist import (
    LightroomCatalogAssetPersister,
    summarize_lightroom_catalog_persistence_outcome,
)
from pixelpast.ingestion.lightroom_catalog.staged import (
    LightroomCatalogIngestionPersistenceScope,
)
from pixelpast.ingestion.lightroom_catalog.transform import (
    LightroomCatalogTransformer,
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
    "LightroomCatalogIngestionPersistenceScope",
    "LightroomCatalogIngestionRunCoordinator",
    "LightroomCatalogLoadProgress",
    "LightroomCatalogAssetPersister",
    "LightroomCatalogTransformer",
    "LIGHTROOM_CATALOG_INITIAL_PHASE",
    "LIGHTROOM_CATALOG_JOB_NAME",
    "LIGHTROOM_CATALOG_JOB_TYPE",
    "LIGHTROOM_CATALOG_MODE",
    "LIGHTROOM_CATALOG_SOURCE_TYPE",
    "build_lightroom_catalog_source_external_id",
    "build_lightroom_catalog_source_name",
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
    "summarize_lightroom_catalog_persistence_outcome",
]
