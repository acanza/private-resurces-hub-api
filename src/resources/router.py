from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from src.resources import service
from src.resources.config import resources_settings
from src.resources.dependencies import valid_category_access, valid_resource_id
from src.resources.schemas import (
    CategoryAccessRequest,
    CategoryAccessResponse,
    ResourceResponse,
)

router = APIRouter(prefix="/resources", tags=["resources"])

ResourceDep = Annotated[dict, Depends(valid_resource_id)]
CategoryAccessDep = Annotated[CategoryAccessRequest, Depends(valid_category_access)]


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
    signed = service.build_cloudfront_signed_cookies(category_id)

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
