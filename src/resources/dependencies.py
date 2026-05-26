from src.resources import service
from src.resources.exceptions import ResourceNotFound


async def valid_resource_id(resource_id: str) -> dict:
    resource = await service.get_resource(resource_id)
    if not resource:
        raise ResourceNotFound()
    return resource
