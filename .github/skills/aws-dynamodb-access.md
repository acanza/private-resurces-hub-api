---
name: aws-dynamodb-access
description: "Use when: reading, writing or updating items in a DynamoDB table, creating a DynamoDB resource dependency, mapping Pydantic models to DynamoDB items, or handling DynamoDB errors (ResourceNotFoundException, ConditionalCheckFailedException)."
---

# AWS DynamoDB Access

## When to use
- Implementing GET endpoints that fetch a single item by primary key
- Implementing POST endpoints that create new items (`put_item`)
- Implementing PUT endpoints that partially update existing items (`update_item`)
- Setting up the aioboto3 DynamoDB resource as a FastAPI dependency
- Handling DynamoDB-specific exceptions and mapping them to HTTP errors

---

## Package and version

```
aioboto3>=13.0    # async boto3 wrapper
boto3>=1.38       # underlying SDK (installed as aioboto3 dependency)
```

Use `aioboto3` for async routes. Never call sync DynamoDB methods inside `async def`.

---

## DynamoDB table dependency

```python
# src/dynamodb/dependencies.py
from typing import Annotated
import aioboto3
from fastapi import Depends
from src.config import settings

_session = aioboto3.Session()


async def get_dynamodb_table():
    async with _session.resource("dynamodb", region_name=settings.AWS_REGION) as resource:
        table = await resource.Table(settings.DYNAMODB_TABLE_NAME)
        yield table


DynamoDBTableDep = Annotated[object, Depends(get_dynamodb_table)]
```

> Credentials are resolved from the environment or IAM role. **Never hardcode them.**

---

## Repository — core DynamoDB operations

```python
# src/dynamodb/repository.py
from typing import Any
from botocore.exceptions import ClientError
from .exceptions import ItemNotFound, ItemAlreadyExists, DynamoDBError


async def get_item(table, item_id: str) -> dict[str, Any]:
    response = await table.get_item(Key={"id": item_id})
    item = response.get("Item")
    if item is None:
        raise ItemNotFound(item_id)
    return item


async def put_item(table, item: dict[str, Any]) -> dict[str, Any]:
    try:
        await table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(id)",  # prevent silent overwrite
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise ItemAlreadyExists(item["id"])
        raise DynamoDBError(str(exc)) from exc
    return item


async def update_item(
    table, item_id: str, updates: dict[str, Any]
) -> dict[str, Any]:
    if not updates:
        return await get_item(table, item_id)

    # Build UpdateExpression dynamically from the updates dict
    set_parts = []
    expr_names: dict[str, str] = {}
    expr_values: dict[str, Any] = {}

    for i, (field, value) in enumerate(updates.items()):
        placeholder_name = f"#f{i}"
        placeholder_value = f":v{i}"
        set_parts.append(f"{placeholder_name} = {placeholder_value}")
        expr_names[placeholder_name] = field
        expr_values[placeholder_value] = value

    try:
        response = await table.update_item(
            Key={"id": item_id},
            UpdateExpression="SET " + ", ".join(set_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression="attribute_exists(id)",   # fail if item does not exist
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            raise ItemNotFound(item_id)
        raise DynamoDBError(str(exc)) from exc

    return response["Attributes"]
```

---

## Domain exceptions → HTTP errors

```python
# src/dynamodb/exceptions.py
from fastapi import HTTPException, status


class ItemNotFound(HTTPException):
    def __init__(self, item_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' not found.",
        )


class ItemAlreadyExists(HTTPException):
    def __init__(self, item_id: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item '{item_id}' already exists.",
        )


class DynamoDBError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DynamoDB error: {detail}",
        )
```

---

## Service layer

```python
# src/dynamodb/service.py
from .repository import get_item as repo_get, put_item as repo_put, update_item as repo_update
from .schemas import ItemCreate, ItemUpdate, ItemResponse


class DynamoDBService:
    def __init__(self, table) -> None:
        self._table = table

    async def get_item(self, item_id: str) -> ItemResponse:
        raw = await repo_get(self._table, item_id)
        return ItemResponse(**raw)

    async def put_item(self, payload: ItemCreate) -> ItemResponse:
        item = payload.model_dump()
        raw = await repo_put(self._table, item)
        return ItemResponse(**raw)

    async def update_item(self, item_id: str, payload: ItemUpdate) -> ItemResponse:
        updates = payload.model_dump(exclude_none=True)
        raw = await repo_update(self._table, item_id, updates)
        return ItemResponse(**raw)
```

---

## Required environment variables

```ini
# .env
AWS_REGION=us-east-1
DYNAMODB_TABLE_NAME=my-table
```

Add to `src/config.py`:

```python
class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    DYNAMODB_TABLE_NAME: str
```

---

## DynamoDB data-type cheatsheet

| Python type  | DynamoDB type | Notes                              |
|--------------|---------------|------------------------------------|
| `str`        | S             | Primary key must be `str` or `int` |
| `int`/`float`| N             | Stored as string internally        |
| `bool`       | BOOL          |                                    |
| `list`       | L             |                                    |
| `dict`       | M             |                                    |
| `None`       | NULL          | Use `exclude_none=True` to skip    |
| `bytes`      | B             | Base64 in JSON responses           |

---

## Security rules

- Restrict the IAM policy to `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem` on the specific table ARN — no `dynamodb:*`.
- Never expose the full DynamoDB item structure if it contains internal/sensitive fields — filter via `ItemResponse` schema.
- Use `ConditionExpression` on writes to prevent silent overwrites and blind updates.
- Do not log `ExpressionAttributeValues` — they may contain sensitive data.
