"""Repository foundation smoke tests."""

from importlib import import_module
from pathlib import Path


def test_root_package_imports() -> None:
    package = import_module("pixelpast")

    assert package.__all__ == [
        "analytics",
        "api",
        "cli",
        "ingestion",
        "persistence",
        "shared",
    ]


def test_architecture_packages_are_importable() -> None:
    for package_name in (
        "pixelpast.persistence",
        "pixelpast.api",
        "pixelpast.ingestion",
        "pixelpast.analytics",
        "pixelpast.cli",
        "pixelpast.shared",
    ):
        assert import_module(package_name) is not None


def test_api_documentation_home_exists() -> None:
    assert Path("doc/api").is_dir()
    assert Path("doc/api/README.md").is_file()
    assert Path("doc/api/openapi.yaml").is_file()
