"""Provider identity helpers for Google Places derived place resolution."""

from __future__ import annotations

from dataclasses import dataclass

from pixelpast.persistence.repositories import SourceRepository, SourceUpsertResult

GOOGLE_PLACES_PROVIDER_SOURCE_TYPE = "google_places_api"
GOOGLE_PLACES_PROVIDER_SOURCE_NAME = "Google Places API"
GOOGLE_PLACES_PROVIDER_EXTERNAL_ID = "google_places_api"


@dataclass(slots=True, frozen=True)
class GooglePlacesProviderSourceDefinition:
    """Deterministic source identity for Google Places derived provenance."""

    external_id: str = GOOGLE_PLACES_PROVIDER_EXTERNAL_ID
    name: str = GOOGLE_PLACES_PROVIDER_SOURCE_NAME
    source_type: str = GOOGLE_PLACES_PROVIDER_SOURCE_TYPE


class GooglePlacesProviderSourceResolver:
    """Create or reuse the provider-owned canonical source row."""

    def __init__(
        self,
        *,
        definition: GooglePlacesProviderSourceDefinition | None = None,
    ) -> None:
        self._definition = definition or GooglePlacesProviderSourceDefinition()

    def resolve(self, *, repository: SourceRepository) -> SourceUpsertResult:
        """Insert or reuse the Google Places provider source deterministically."""

        return repository.upsert_by_external_id(
            external_id=self._definition.external_id,
            name=self._definition.name,
            source_type=self._definition.source_type,
            config={},
        )
