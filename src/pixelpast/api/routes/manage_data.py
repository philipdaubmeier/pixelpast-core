"""Routes for explicit manage-data catalog loading and batch saving."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from pixelpast.api.dependencies import get_db_session
from pixelpast.api.routes.metadata import (
    BAD_REQUEST_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    combine_responses,
)
from pixelpast.api.schemas import (
    PersonGroupsCatalogResponse,
    PersonGroupMembershipResponse,
    PersonsCatalogResponse,
    SavePersonGroupMembershipRequest,
    SavePersonGroupsCatalogRequest,
    SavePersonsCatalogRequest,
)
from pixelpast.api.services.manage_data import (
    ManageDataCatalogService,
    ManageDataValidationError,
)
from pixelpast.persistence.repositories.manage_data import (
    ManageDataPersonGroupRepository,
    ManageDataPersonRepository,
)

router = APIRouter(tags=["manage-data"])

PERSONS_CATALOG_EXAMPLES = {
    "family_catalog": {
        "summary": "Loaded persons catalog",
        "value": {
            "persons": [
                {
                    "id": 7,
                    "name": "Anna Becker",
                    "aliases": ["Anna B.", "Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 12,
                    "name": "Milo Tan",
                    "aliases": [],
                    "path": None,
                },
            ]
        },
    }
}

SAVE_PERSONS_EXAMPLES = {
    "upsert_people": {
        "summary": "Create and update person rows",
        "value": {
            "persons": [
                {
                    "id": 7,
                    "name": "Anna Becker",
                    "aliases": ["Anna B.", "Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "name": "Milo Tan",
                    "aliases": ["Miles"],
                    "path": "friends/milo-tan",
                },
            ],
            "delete_ids": [],
        },
    },
    "rejected_delete_semantics": {
        "summary": "Delete semantics are reserved for later",
        "value": {
            "persons": [],
            "delete_ids": [12],
        },
    },
}

PERSON_GROUPS_CATALOG_EXAMPLES = {
    "managed_groups": {
        "summary": "Loaded manual person-group catalog",
        "value": {
            "person_groups": [
                {"id": 3, "name": "Immediate Family", "member_count": 4},
                {"id": 8, "name": "Berlin Friends", "member_count": 7},
            ]
        },
    }
}

SAVE_PERSON_GROUPS_EXAMPLES = {
    "replace_groups": {
        "summary": "Create, update, and delete manual groups",
        "value": {
            "person_groups": [
                {"id": 3, "name": "Immediate Family"},
                {"name": "Travel Buddies"},
            ],
            "delete_ids": [8],
        },
    }
}

PERSON_GROUP_MEMBERSHIP_EXAMPLES = {
    "loaded_membership": {
        "summary": "Loaded one group's persisted members",
        "value": {
            "person_group": {
                "id": 3,
                "name": "Immediate Family",
                "member_count": 2,
            },
            "members": [
                {
                    "id": 7,
                    "name": "Anna Becker",
                    "aliases": ["Annie"],
                    "path": "family/anna-becker",
                },
                {
                    "id": 12,
                    "name": "Milo Tan",
                    "aliases": [],
                    "path": "friends/milo-tan",
                },
            ],
        },
    }
}

SAVE_PERSON_GROUP_MEMBERSHIP_EXAMPLES = {
    "replace_membership": {
        "summary": "Replace one group's persisted member set",
        "value": {
            "person_ids": [7, 12, 18],
        },
    }
}

MANAGE_DATA_BAD_REQUEST_EXAMPLES = {
    **BAD_REQUEST_RESPONSE[400]["content"]["application/json"]["examples"],
    "duplicate_person_path": {
        "summary": "Two persons claim the same path",
        "value": {"detail": "person path 'family/anna-becker' must be unique"},
    },
    "person_delete_forbidden": {
        "summary": "Persons cannot be deleted in v1",
        "value": {
            "detail": (
                "person deletion is not supported in the v1 manage-data contract"
            )
        },
    },
}


@router.get(
    "/manage-data/persons",
    response_model=PersonsCatalogResponse,
    summary="Get persons catalog",
    description=(
        "Return the canonical persons catalog used by the manage-data workspace. "
        "Rows are delivered in deterministic display order."
    ),
    response_description="Canonical persons catalog for manual maintenance.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSONS_CATALOG_EXAMPLES,
                    }
                }
            }
        },
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_persons_catalog(
    session: Session = Depends(get_db_session),
) -> PersonsCatalogResponse:
    """Return the canonical persons catalog for the manage-data UI."""

    service = _build_manage_data_catalog_service(session)
    return service.get_persons_catalog()


@router.put(
    "/manage-data/persons",
    response_model=PersonsCatalogResponse,
    summary="Save persons catalog draft",
    description=(
        "Create and update canonical persons as one batch save. "
        "Deletion semantics are explicitly rejected in the v1 contract."
    ),
    response_description="Reloaded canonical persons catalog after persistence.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSONS_CATALOG_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": MANAGE_DATA_BAD_REQUEST_EXAMPLES,
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def save_persons_catalog(
    request: SavePersonsCatalogRequest = Body(
        ...,
        openapi_examples=SAVE_PERSONS_EXAMPLES,
    ),
    session: Session = Depends(get_db_session),
) -> PersonsCatalogResponse:
    """Persist one section-scoped persons draft and return persisted truth."""

    service = _build_manage_data_catalog_service(session)
    try:
        response = service.save_persons_catalog(
            persons=request.persons,
            delete_ids=request.delete_ids,
        )
        session.commit()
        return response
    except ManageDataValidationError as error:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/manage-data/person-groups",
    response_model=PersonGroupsCatalogResponse,
    summary="Get person-group catalog",
    description=(
        "Return the manually managed canonical person-group catalog with "
        "read-only member counts."
    ),
    response_description="Canonical person-group catalog for manual maintenance.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSON_GROUPS_CATALOG_EXAMPLES,
                    }
                }
            }
        },
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_person_groups_catalog(
    session: Session = Depends(get_db_session),
) -> PersonGroupsCatalogResponse:
    """Return the canonical person-group catalog for the manage-data UI."""

    service = _build_manage_data_catalog_service(session)
    return service.get_person_groups_catalog()


@router.put(
    "/manage-data/person-groups",
    response_model=PersonGroupsCatalogResponse,
    summary="Save person-group catalog draft",
    description=(
        "Create, update, and delete manual canonical person groups as one "
        "batch save. Member counts remain server-owned read data."
    ),
    response_description="Reloaded canonical person-group catalog after persistence.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSON_GROUPS_CATALOG_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": BAD_REQUEST_RESPONSE[400]["content"][
                            "application/json"
                        ]["examples"],
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def save_person_groups_catalog(
    request: SavePersonGroupsCatalogRequest = Body(
        ...,
        openapi_examples=SAVE_PERSON_GROUPS_EXAMPLES,
    ),
    session: Session = Depends(get_db_session),
) -> PersonGroupsCatalogResponse:
    """Persist one section-scoped person-group draft and return persisted truth."""

    service = _build_manage_data_catalog_service(session)
    try:
        response = service.save_person_groups_catalog(
            person_groups=request.person_groups,
            delete_ids=request.delete_ids,
        )
        session.commit()
        return response
    except ManageDataValidationError as error:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get(
    "/manage-data/person-groups/{group_id}/members",
    response_model=PersonGroupMembershipResponse,
    summary="Get one person-group membership set",
    description=(
        "Return one canonical person group in focus together with its current "
        "persisted members."
    ),
    response_description="Focused person-group membership state for manual maintenance.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSON_GROUP_MEMBERSHIP_EXAMPLES,
                    }
                }
            }
        },
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def get_person_group_membership(
    group_id: int,
    session: Session = Depends(get_db_session),
) -> PersonGroupMembershipResponse:
    """Return one person group's persisted member set."""

    service = _build_manage_data_catalog_service(session)
    try:
        return service.get_person_group_membership(group_id=group_id)
    except ManageDataValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put(
    "/manage-data/person-groups/{group_id}/members",
    response_model=PersonGroupMembershipResponse,
    summary="Save one person-group membership draft",
    description=(
        "Replace one canonical person group's persisted membership set as one "
        "authoritative batch."
    ),
    response_description="Reloaded person-group membership state after persistence.",
    responses=combine_responses(
        {
            200: {
                "content": {
                    "application/json": {
                        "examples": PERSON_GROUP_MEMBERSHIP_EXAMPLES,
                    }
                }
            }
        },
        {
            400: {
                **BAD_REQUEST_RESPONSE[400],
                "content": {
                    "application/json": {
                        "examples": BAD_REQUEST_RESPONSE[400]["content"][
                            "application/json"
                        ]["examples"],
                    }
                },
            }
        },
        VALIDATION_ERROR_RESPONSE,
    ),
)
def save_person_group_membership(
    group_id: int,
    request: SavePersonGroupMembershipRequest = Body(
        ...,
        openapi_examples=SAVE_PERSON_GROUP_MEMBERSHIP_EXAMPLES,
    ),
    session: Session = Depends(get_db_session),
) -> PersonGroupMembershipResponse:
    """Persist one focused person-group membership draft and return persisted truth."""

    service = _build_manage_data_catalog_service(session)
    try:
        response = service.save_person_group_membership(
            group_id=group_id,
            person_ids=request.person_ids,
        )
        session.commit()
        return response
    except ManageDataValidationError as error:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(error)) from error


def _build_manage_data_catalog_service(session: Session) -> ManageDataCatalogService:
    """Build the explicit manage-data service boundary."""

    return ManageDataCatalogService(
        person_repository=ManageDataPersonRepository(session),
        person_group_repository=ManageDataPersonGroupRepository(session),
    )
