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

__all__ = [
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
]
