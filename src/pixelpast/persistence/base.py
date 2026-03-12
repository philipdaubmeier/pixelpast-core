"""SQLAlchemy declarative base for persistence mappings."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for ORM models."""


# Import ORM mappings so metadata is populated for runtime and Alembic.
import pixelpast.persistence.models  # noqa: E402,F401
