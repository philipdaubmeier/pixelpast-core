"""Shared pytest fixtures and test-session housekeeping."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_VAR_ROOT = Path("var")
_PRESERVED_VAR_ENTRIES = {"pixelpast.db"}


@pytest.fixture(scope="session", autouse=True)
def clean_test_artifacts_under_var() -> None:
    """Remove stale and newly-created test artifacts under ``var``.

    The application database ``var/pixelpast.db`` is explicitly preserved.
    """

    _cleanup_var_directory()
    yield
    _cleanup_var_directory()


def _cleanup_var_directory() -> None:
    if not _VAR_ROOT.exists():
        return

    for path in _VAR_ROOT.iterdir():
        if path.name in _PRESERVED_VAR_ENTRIES:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
