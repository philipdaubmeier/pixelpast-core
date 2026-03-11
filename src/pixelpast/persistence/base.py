"""SQLAlchemy declarative base for persistence mappings."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for ORM models."""
