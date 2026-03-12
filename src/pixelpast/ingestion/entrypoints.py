"""Ingestion command entrypoints."""

import logging

from pixelpast.shared.runtime import RuntimeContext

logger = logging.getLogger(__name__)

_SUPPORTED_SOURCES = frozenset({"photos"})


def run_ingest_source(*, source: str, runtime: RuntimeContext) -> None:
    """Run a stub ingestion entrypoint for a source."""

    if source not in _SUPPORTED_SOURCES:
        available_sources = ", ".join(sorted(_SUPPORTED_SOURCES))
        raise ValueError(
            f"Unsupported source '{source}'. Available stub sources: {available_sources}."
        )

    logger.info(
        "ingest stub executed",
        extra={
            "source": source,
            "database_url": runtime.settings.database_url,
            "status": "stub",
        },
    )
