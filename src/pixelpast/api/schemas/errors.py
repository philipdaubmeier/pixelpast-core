"""Shared error schemas for documented API error responses."""

from __future__ import annotations

from pydantic import BaseModel


class ApiErrorResponse(BaseModel):
    """Error payload for contract-level request rejections."""

    detail: str


class ApiValidationErrorItem(BaseModel):
    """One FastAPI request validation error entry."""

    type: str
    loc: list[str | int]
    msg: str
    input: object | None = None


class ApiValidationErrorResponse(BaseModel):
    """Error payload returned when declared request validation fails."""

    detail: list[ApiValidationErrorItem]
