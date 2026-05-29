from src.resources import service
from src.resources.exceptions import AccessDeniedError, ResourceNotFoundError
from src.resources.schemas import CategoryAccessRequest


async def valid_resource_id(resource_id: str) -> dict:
    resource = await service.get_resource(resource_id)
    if not resource:
        raise ResourceNotFoundError()
    return resource


async def valid_category_access(
    category_id: str,
    payload: CategoryAccessRequest,
) -> CategoryAccessRequest:
    has_access = await service.check_user_access(payload.email, category_id)
    if not has_access:
        raise AccessDeniedError()
    return payload
