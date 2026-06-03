from typing import Annotated

from fastapi import APIRouter, Body, Depends, Response, status

from src.resources import service
from src.resources.config import resources_settings
from src.resources.dependencies import valid_category_access, valid_resource_id
from src.resources.schemas import (
    CategoryAccessRequest,
    CategoryAccessResponse,
    CategoryItemsResponse,
    ResourceListResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])

ResourceDep = Annotated[dict, Depends(valid_resource_id)]
CategoryAccessDep = Annotated[CategoryAccessRequest, Depends(valid_category_access)]


@router.post(
    "/",
    response_model=ResourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all resources with access information",
    description=(
        "Lists all directories in the S3 bucket with user's "
        "access permissions. Requires Bearer token authentication "
        "from Cognito."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "User does not have access"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Upstream AWS error"},
    },
)
async def list_resources(payload: CategoryAccessRequest) -> ResourceListResponse:
    resources = await service.list_resources_with_access(payload.email)
    return ResourceListResponse(resources=resources)


@router.get(
    "/{category_id}",
    response_model=CategoryItemsResponse,
    status_code=status.HTTP_200_OK,
    summary="List items in a category with signed URLs",
    description=(
        "Lists all items in a category directory with CloudFront signed URLs. "
        "Requires Bearer token authentication from Cognito and user must have "
        "access to the category."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "User does not have access"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Upstream AWS error"},
    },
)
async def get_category_items(
    category_id: str,
    payload: Annotated[CategoryAccessRequest, Body()],
) -> CategoryItemsResponse:
    items = await service.list_category_items_with_signed_urls(
        payload.email, category_id
    )
    return CategoryItemsResponse(items=items)


@router.post(
    "/{category_id}/access",
    response_model=CategoryAccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Request access to a category folder",
    description=(
        "Validates user permissions for the requested category, issues CloudFront "
        "signed cookies, and returns the base CloudFront URL. The browser can then "
        "use those cookies to stream objects directly from CloudFront."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "User does not have access"},
        status.HTTP_502_BAD_GATEWAY: {"description": "Upstream AWS error"},
    },
)
async def request_category_access(
    category_id: str,
    access: CategoryAccessDep,
    response: Response,
) -> CategoryAccessResponse:
    signed = await service.build_cloudfront_signed_cookies(category_id)

    cookie_attrs = {
        "secure": True,
        "httponly": True,
        "samesite": "none",
        "domain": resources_settings.CF_DISTRIBUTION_DOMAIN,
        "path": "/",
        "max_age": resources_settings.CF_COOKIE_MAX_AGE_SECONDS,
    }
    for name, value in signed.cookies.items():
        response.set_cookie(key=name, value=value, **cookie_attrs)

    return CategoryAccessResponse(
        cloudfront_url=(
            f"https://{resources_settings.CF_DISTRIBUTION_DOMAIN}/{category_id}/"
        ),
        expires_at=signed.expires_at,
    )
