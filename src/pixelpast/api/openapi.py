"""OpenAPI export helpers for repository-managed API contracts."""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from pixelpast.api.app import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OPENAPI_EXPORT_PATH = REPOSITORY_ROOT / "doc" / "api" / "openapi.yaml"


def export_openapi_schema(*, output_path: Path = DEFAULT_OPENAPI_EXPORT_PATH) -> Path:
    """Export the current FastAPI OpenAPI contract to the canonical repository path."""

    app = create_app()
    try:
        schema = app.openapi()
    finally:
        _dispose_app_engine(app)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_yaml_document(schema), encoding="utf-8")
    return output_path


def _dispose_app_engine(app: FastAPI) -> None:
    """Dispose the SQLAlchemy engine attached to the application state."""

    engine = getattr(app.state, "engine", None)
    if isinstance(engine, Engine):
        engine.dispose()


def _render_yaml_document(value: Any) -> str:
    """Render one JSON-compatible value as stable block-style YAML."""

    return _render_yaml_value(value, indent=0) + "\n"


def _render_yaml_value(value: Any, *, indent: int) -> str:
    if isinstance(value, dict):
        if not value:
            return f"{' ' * indent}{{}}"
        lines: list[str] = []
        for key, nested_value in value.items():
            rendered_key = json.dumps(str(key), ensure_ascii=False)
            if _is_inline_value(nested_value):
                lines.append(
                    f"{' ' * indent}{rendered_key}: {_render_inline_value(nested_value)}"
                )
                continue
            lines.append(f"{' ' * indent}{rendered_key}:")
            lines.append(_render_yaml_value(nested_value, indent=indent + 2))
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return f"{' ' * indent}[]"
        lines = []
        for item in value:
            prefix = f"{' ' * indent}-"
            if _is_inline_value(item):
                lines.append(f"{prefix} {_render_inline_value(item)}")
                continue
            lines.append(prefix)
            lines.append(_render_yaml_value(item, indent=indent + 2))
        return "\n".join(lines)

    return f"{' ' * indent}{_render_scalar(value)}"


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _is_inline_value(value: Any) -> bool:
    return _is_scalar(value) or value == {} or value == []


def _render_inline_value(value: Any) -> str:
    if value == {}:
        return "{}"
    if value == []:
        return "[]"
    return _render_scalar(value)


def _render_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
