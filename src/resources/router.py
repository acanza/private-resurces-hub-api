from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.resources.dependencies import valid_resource_id
from src.resources.schemas import ResourceResponse

router = APIRouter(prefix="/resources", tags=["resources"])

ResourceDep = Annotated[dict, Depends(valid_resource_id)]


@router.get(
    "/{resource_id}",
    response_model=ResourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a resource by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
    },
)
async def get_resource(resource: ResourceDep) -> ResourceResponse:
    return resource
