"""Repository foundation smoke tests."""

from importlib import import_module


def test_root_package_imports() -> None:
    package = import_module("pixelpast")

    assert package.__all__ == [
        "analytics",
        "api",
        "cli",
        "domain",
        "ingestion",
        "persistence",
        "shared",
    ]


def test_architecture_packages_are_importable() -> None:
    for package_name in (
        "pixelpast.domain",
        "pixelpast.persistence",
        "pixelpast.api",
        "pixelpast.ingestion",
        "pixelpast.analytics",
        "pixelpast.cli",
        "pixelpast.shared",
    ):
        assert import_module(package_name) is not None
