"""Explicit request and response schemas for the REST API."""

from pixelpast.api.schemas.bootstrap_ui import (
    ExplorationBootstrapResponse,
    ExplorationPerson,
    ExplorationRange,
    ExplorationTag,
    ExplorationViewMode,
)
from pixelpast.api.schemas.day_detail import (
    DayAssetItem,
    DayDetailResponse,
    DayEventItem,
)
from pixelpast.api.schemas.errors import (
    ApiErrorResponse,
    ApiValidationErrorItem,
    ApiValidationErrorResponse,
)
from pixelpast.api.schemas.daygrid import (
    ExplorationGridDay,
    ExplorationGridResponse,
)
from pixelpast.api.schemas.hovercontext import (
    DayContextDay,
    DayContextMapPoint,
    DayContextResponse,
    DayContextSummaryCounts,
)
from pixelpast.api.schemas.manage_data import (
    PersonCatalogEntry,
    PersonCatalogWriteEntry,
    PersonGroupCatalogEntry,
    PersonGroupCatalogWriteEntry,
    PersonGroupMembershipGroupEntry,
    PersonGroupMembershipMemberEntry,
    PersonGroupMembershipResponse,
    PersonGroupsCatalogResponse,
    PersonsCatalogResponse,
    SavePersonGroupMembershipRequest,
    SavePersonGroupsCatalogRequest,
    SavePersonsCatalogRequest,
)
from pixelpast.api.schemas.social_graph import (
    SocialGraphLink,
    SocialGraphPerson,
    SocialGraphResponse,
)

__all__ = [
    "ApiErrorResponse",
    "ApiValidationErrorItem",
    "ApiValidationErrorResponse",
    "DayAssetItem",
    "DayContextDay",
    "DayContextMapPoint",
    "DayContextResponse",
    "DayContextSummaryCounts",
    "DayDetailResponse",
    "DayEventItem",
    "ExplorationBootstrapResponse",
    "ExplorationGridDay",
    "ExplorationGridResponse",
    "ExplorationPerson",
    "ExplorationRange",
    "ExplorationTag",
    "ExplorationViewMode",
    "PersonCatalogEntry",
    "PersonCatalogWriteEntry",
    "PersonGroupCatalogEntry",
    "PersonGroupCatalogWriteEntry",
    "PersonGroupMembershipGroupEntry",
    "PersonGroupMembershipMemberEntry",
    "PersonGroupMembershipResponse",
    "PersonGroupsCatalogResponse",
    "PersonsCatalogResponse",
    "SavePersonGroupMembershipRequest",
    "SavePersonGroupsCatalogRequest",
    "SavePersonsCatalogRequest",
    "SocialGraphLink",
    "SocialGraphPerson",
    "SocialGraphResponse",
]
