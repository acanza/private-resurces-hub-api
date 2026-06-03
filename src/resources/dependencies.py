from typing import Annotated

from fastapi import Body

from src.resources import service
from src.resources.exceptions import AccessDeniedError
from src.resources.schemas import CategoryAccessRequest


async def valid_category_access(
    category_id: str,
    payload: Annotated[CategoryAccessRequest, Body()],
) -> CategoryAccessRequest:
    has_access = await service.check_user_access(payload.email, category_id)
    if not has_access:
        raise AccessDeniedError()
    return payload
