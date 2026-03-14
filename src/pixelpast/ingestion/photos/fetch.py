"""Exiftool-backed metadata fetching for photo ingestion."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, Callable

from pixelpast.ingestion.photos.contracts import PhotoMetadataBatchProgress

_EXIFTOOL_BATCH_SIZE = 85
_EXIFTOOL_BATCH_TIMEOUT_SECONDS = 120
_EXIFTOOL_METADATA_PARAMS = ("-n", "-a", "-G1", "-s")

logger = logging.getLogger(__name__)


class PhotoMetadataFetcher:
    """Fetch grouped metadata for resolved photo paths via exiftool."""

    def extract_metadata_by_path(
        self,
        *,
        paths: list[Path],
        on_batch_progress: Callable[[PhotoMetadataBatchProgress], None] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return raw exiftool metadata indexed by resolved source path."""

        if not paths:
            return {}

        resolved_paths = [path.expanduser().resolve() for path in paths]
        metadata_by_path: dict[str, dict[str, Any]] = {}
        all_batches = _metadata_batches_for_paths(resolved_paths)
        batch_total = len(all_batches)

        try:
            for batch_index, batch_paths in enumerate(all_batches, start=1):
                if on_batch_progress is not None:
                    on_batch_progress(
                        PhotoMetadataBatchProgress(
                            event="submitted",
                            batch_index=batch_index,
                            batch_total=batch_total,
                            batch_size=len(batch_paths),
                        )
                    )
                batch_metadata = self._extract_batch_metadata_with_fallback(
                    batch_paths=batch_paths,
                )
                metadata_by_path.update(
                    _index_metadata_results(
                        metadata=batch_metadata,
                        expected_paths=batch_paths,
                    )
                )
                if on_batch_progress is not None:
                    on_batch_progress(
                        PhotoMetadataBatchProgress(
                            event="completed",
                            batch_index=batch_index,
                            batch_total=batch_total,
                            batch_size=len(batch_paths),
                        )
                    )
        except (FileNotFoundError, OSError) as error:
            raise RuntimeError(
                "Photo ingestion requires exiftool to be installed and callable."
            ) from error

        return metadata_by_path

    def _extract_batch_metadata_with_fallback(
        self,
        *,
        batch_paths: list[Path],
    ) -> list[dict[str, Any]]:
        """Extract one exiftool batch, splitting recursively on timeouts."""

        try:
            return _run_exiftool_json(paths=batch_paths)
        except subprocess.TimeoutExpired:
            if len(batch_paths) == 1:
                timed_out_path = batch_paths[0].as_posix()
                logger.warning(
                    "photo ingest metadata extraction timed out for file",
                    extra={
                        "path": timed_out_path,
                        "timeout_seconds": _EXIFTOOL_BATCH_TIMEOUT_SECONDS,
                    },
                )
                return [{"SourceFile": timed_out_path}]

            midpoint = len(batch_paths) // 2
            left_paths = batch_paths[:midpoint]
            right_paths = batch_paths[midpoint:]
            logger.warning(
                "photo ingest metadata batch timed out, splitting batch",
                extra={
                    "batch_size": len(batch_paths),
                    "left_batch_size": len(left_paths),
                    "right_batch_size": len(right_paths),
                    "timeout_seconds": _EXIFTOOL_BATCH_TIMEOUT_SECONDS,
                },
            )
            return [
                *self._extract_batch_metadata_with_fallback(batch_paths=left_paths),
                *self._extract_batch_metadata_with_fallback(batch_paths=right_paths),
            ]


def count_photo_metadata_batches(path_count: int) -> int:
    """Return the deterministic metadata batch count for a discovered path total."""

    if path_count <= 0:
        return 0
    if path_count == 1:
        return 1
    return 1 + ((path_count - 1 + _EXIFTOOL_BATCH_SIZE - 1) // _EXIFTOOL_BATCH_SIZE)


def _chunked(paths: Iterable[Path], chunk_size: int) -> Iterator[list[Path]]:
    """Yield stable fixed-size path chunks."""

    batch: list[Path] = []
    for path in paths:
        batch.append(path)
        if len(batch) == chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _metadata_batches_for_paths(paths: list[Path]) -> list[list[Path]]:
    """Return the exiftool metadata batches for a resolved path list."""

    if not paths:
        return []
    if len(paths) == 1:
        return [[paths[0]]]
    return [[paths[0]], *_chunked(paths[1:], _EXIFTOOL_BATCH_SIZE)]


def _index_metadata_results(
    *,
    metadata: list[Any],
    expected_paths: list[Path],
) -> dict[str, dict[str, Any]]:
    """Index exiftool metadata results by absolute source path."""

    indexed: dict[str, dict[str, Any]] = {
        path.as_posix(): {} for path in expected_paths
    }
    for entry in metadata:
        if not isinstance(entry, dict):
            continue
        source_file = entry.get("SourceFile")
        if not isinstance(source_file, str):
            continue
        indexed[Path(source_file).expanduser().resolve().as_posix()] = entry
    return indexed


def _run_exiftool_json(*, paths: list[Path]) -> list[dict[str, Any]]:
    """Execute one exiftool metadata batch with a bounded timeout."""

    executable = shutil.which("exiftool")
    if executable is None:
        raise FileNotFoundError("exiftool")

    command = [
        executable,
        "-j",
        *list(_EXIFTOOL_METADATA_PARAMS),
        *[path.as_posix() for path in paths],
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=_EXIFTOOL_BATCH_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.stdout == "":
        raise RuntimeError(
            f"Exiftool returned no metadata output for batch of {len(paths)} file(s)."
        )

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Exiftool returned invalid JSON metadata output.") from error
    if not isinstance(parsed, list):
        raise RuntimeError("Exiftool returned an unexpected metadata payload shape.")
    return [entry for entry in parsed if isinstance(entry, dict)]


__all__ = ["PhotoMetadataBatchProgress", "PhotoMetadataFetcher", "count_photo_metadata_batches"]
