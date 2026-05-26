---
name: fastapi-route-scaffolding
description: "Use when: scaffolding a new FastAPI router, adding endpoints for S3 or DynamoDB domains, creating Pydantic schemas for AWS responses, or wiring a new domain into main.py."
---

# FastAPI Route Scaffolding

## When to use
- Adding a new `APIRouter` for a domain (e.g. `s3`, `dynamodb`)
- Creating GET endpoints for S3 object access
- Creating GET / POST / PUT endpoints for DynamoDB items
- Wiring a new router into `main.py`

---

## File layout for a new domain

```
src/
└── {domain}/           # e.g. s3/, dynamodb/
    ├── router.py       # APIRouter + route handlers
    ├── schemas.py      # Pydantic request/response models
    ├── service.py      # Business logic (calls repository)
    ├── repository.py   # Direct AWS SDK calls
    ├── dependencies.py # Domain-scoped FastAPI dependencies
    └── exceptions.py   # Domain HTTP exceptions
```

---

## Router template

```python
# src/{domain}/router.py
from fastapi import APIRouter, status
from typing import Annotated
from .dependencies import ...
from .schemas import ...
from .service import ...

router = APIRouter(prefix="/api/v1/{domain}", tags=["{domain}"])
```

Register in `main.py`:

```python
from src.s3 import router as s3_router
from src.dynamodb import router as dynamodb_router

app.include_router(s3_router)
app.include_router(dynamodb_router)
```

---

## S3 domain — read-only routes

```python
# src/s3/router.py
from fastapi import APIRouter, status
from typing import Annotated
from .dependencies import S3ServiceDep
from .schemas import S3ObjectResponse, S3ObjectListResponse

router = APIRouter(prefix="/api/v1/s3", tags=["s3"])


@router.get(
    "/{bucket}/objects",
    response_model=S3ObjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List objects in a bucket",
)
async def list_objects(bucket: str, service: S3ServiceDep) -> S3ObjectListResponse:
    return await service.list_objects(bucket)


@router.get(
    "/{bucket}/objects/{key:path}",
    response_model=S3ObjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an object from a bucket",
)
async def get_object(bucket: str, key: str, service: S3ServiceDep) -> S3ObjectResponse:
    return await service.get_object(bucket, key)
```

### S3 schemas

```python
# src/s3/schemas.py
from pydantic import BaseModel
from datetime import datetime


class S3ObjectMeta(BaseModel):
    key: str
    size: int
    last_modified: datetime
    etag: str


class S3ObjectListResponse(BaseModel):
    bucket: str
    objects: list[S3ObjectMeta]
    count: int


class S3ObjectResponse(BaseModel):
    bucket: str
    key: str
    content_type: str
    body: str          # base64-encoded for binary; plain text for text objects
    size: int
```

---

## DynamoDB domain — read / write / update routes

```python
# src/dynamodb/router.py
from fastapi import APIRouter, status
from typing import Annotated
from .dependencies import DynamoDBServiceDep
from .schemas import ItemResponse, ItemCreate, ItemUpdate

router = APIRouter(prefix="/api/v1/items", tags=["items"])


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an item by ID",
)
async def get_item(item_id: str, service: DynamoDBServiceDep) -> ItemResponse:
    return await service.get_item(item_id)


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new item",
)
async def create_item(payload: ItemCreate, service: DynamoDBServiceDep) -> ItemResponse:
    return await service.put_item(payload)


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing item",
)
async def update_item(
    item_id: str, payload: ItemUpdate, service: DynamoDBServiceDep
) -> ItemResponse:
    return await service.update_item(item_id, payload)
```

### DynamoDB schemas

```python
# src/dynamodb/schemas.py
from pydantic import BaseModel, Field
from typing import Any


class ItemCreate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    data: dict[str, Any]


class ItemUpdate(BaseModel):
    data: dict[str, Any]


class ItemResponse(BaseModel):
    id: str
    data: dict[str, Any]
```

---

## Dependency pattern

Expose the service as an `Annotated` type alias so route signatures stay concise:

```python
# src/{domain}/dependencies.py
from typing import Annotated
from fastapi import Depends
from .service import S3Service   # or DynamoDBService

async def get_s3_service() -> S3Service:
    return S3Service()

S3ServiceDep = Annotated[S3Service, Depends(get_s3_service)]
```

---

## Checklist before committing a new route

- [ ] `response_model` declared on every endpoint
- [ ] `status_code` explicit (use `status.HTTP_*` constants)
- [ ] `summary` and `tags` filled in
- [ ] Input validated via Pydantic schema, not inside the handler
- [ ] AWS calls delegated to `service.py` / `repository.py`, not inlined in the router
- [ ] HTTP exceptions raised via `src/{domain}/exceptions.py`, not raw `HTTPException` in the router
