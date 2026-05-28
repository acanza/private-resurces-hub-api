from src.resources import service
from src.resources.exceptions import AccessDenied, ResourceNotFound
from src.resources.schemas import CategoryAccessRequest


async def valid_resource_id(resource_id: str) -> dict:
    resource = await service.get_resource(resource_id)
    if not resource:
        raise ResourceNotFound()
    return resource


async def valid_category_access(
    category_id: str,
    payload: CategoryAccessRequest,
) -> CategoryAccessRequest:
    has_access = await service.check_user_access(payload.email, category_id)
    if not has_access:
        raise AccessDenied()
    return payload
