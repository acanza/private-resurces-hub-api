---
name: fastapi-aws-testing
description: "Use when: writing tests for FastAPI routes that call S3 or DynamoDB, mocking AWS services with moto, overriding boto3 dependencies via dependency_overrides, or setting up pytest fixtures for AWS integration tests."
---

# FastAPI + AWS Testing

## When to use
- Writing integration tests for S3 read endpoints
- Writing integration tests for DynamoDB read / write / update endpoints
- Setting up pytest fixtures that mock AWS services locally with `moto`
- Overriding `get_s3_client` or `get_dynamodb_table` dependencies in tests

---

## Packages

```
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27
moto[s3,dynamodb]>=5.0
```

---

## pytest configuration

```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## Shared AWS fixtures

```python
# tests/conftest.py
import boto3
import pytest
from httpx import AsyncClient, ASGITransport
from moto import mock_aws

from src.main import app
from src.config import settings


# ── moto scope: wrap the entire test session ──────────────────────────
@pytest.fixture(scope="session")
def aws_credentials(monkeypatch_session):
    """Prevent accidental calls to real AWS."""
    monkeypatch_session.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch_session.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch_session.setenv("AWS_DEFAULT_REGION", settings.AWS_REGION)


# ── S3 fixtures ────────────────────────────────────────────────────────
@pytest.fixture
def s3_bucket(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name=settings.AWS_REGION)
        client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
        yield client


# ── DynamoDB fixtures ──────────────────────────────────────────────────
@pytest.fixture
def dynamodb_table(aws_credentials):
    with mock_aws():
        resource = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
        table = resource.create_table(
            TableName=settings.DYNAMODB_TABLE_NAME,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(
            TableName=settings.DYNAMODB_TABLE_NAME
        )
        yield table


# ── HTTP client ────────────────────────────────────────────────────────
@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

---

## Overriding AWS dependencies in tests

Use `app.dependency_overrides` — never monkeypatch boto3 internals directly.

### S3 override

```python
# tests/s3/conftest.py
import boto3
import pytest
from moto import mock_aws
from src.main import app
from src.s3.dependencies import get_s3_client
from src.config import settings


@pytest.fixture(autouse=True)
def override_s3(s3_bucket):
    """Replace the real aioboto3 client with a moto-backed boto3 client."""

    async def fake_s3_client():
        yield boto3.client("s3", region_name=settings.AWS_REGION)

    app.dependency_overrides[get_s3_client] = fake_s3_client
    yield
    app.dependency_overrides.clear()
```

### DynamoDB override

```python
# tests/dynamodb/conftest.py
import boto3
import pytest
from src.main import app
from src.dynamodb.dependencies import get_dynamodb_table
from src.config import settings


@pytest.fixture(autouse=True)
def override_dynamodb(dynamodb_table):
    async def fake_table():
        yield dynamodb_table

    app.dependency_overrides[get_dynamodb_table] = fake_table
    yield
    app.dependency_overrides.clear()
```

---

## S3 route tests

```python
# tests/s3/test_router.py
import pytest
from httpx import AsyncClient


async def test_list_objects_empty_bucket(client: AsyncClient):
    resp = await client.get("/api/v1/s3/my-bucket/objects")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


async def test_get_object_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/s3/my-bucket/objects/missing-key.txt")
    assert resp.status_code == 404


async def test_get_object_ok(client: AsyncClient, s3_bucket):
    s3_bucket.put_object(Bucket="my-bucket", Key="hello.txt", Body=b"hello world")

    resp = await client.get("/api/v1/s3/my-bucket/objects/hello.txt")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "hello.txt"
    assert data["size"] == 11
```

---

## DynamoDB route tests

```python
# tests/dynamodb/test_router.py
import pytest
from httpx import AsyncClient


async def test_get_item_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/items/nonexistent")
    assert resp.status_code == 404


async def test_create_item(client: AsyncClient):
    payload = {"id": "item-1", "data": {"name": "Test"}}
    resp = await client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 201
    assert resp.json()["id"] == "item-1"


async def test_create_item_conflict(client: AsyncClient):
    payload = {"id": "item-dup", "data": {"name": "A"}}
    await client.post("/api/v1/items/", json=payload)
    resp = await client.post("/api/v1/items/", json=payload)
    assert resp.status_code == 409


async def test_update_item(client: AsyncClient):
    await client.post("/api/v1/items/", json={"id": "item-2", "data": {"name": "Old"}})
    resp = await client.put("/api/v1/items/item-2", json={"data": {"name": "New"}})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New"


async def test_update_item_not_found(client: AsyncClient):
    resp = await client.put("/api/v1/items/ghost", json={"data": {"name": "X"}})
    assert resp.status_code == 404
```

---

## Testing rules

- Always use `moto` — never hit real AWS in unit or integration tests.
- Override dependencies with `app.dependency_overrides`, not by patching boto3 internals.
- Reset `dependency_overrides` after each test (use `yield` + `.clear()`).
- Do not share mutable moto state between tests — create fresh resources per test or use `scope="function"` fixtures.
- `asyncio_mode = "auto"` in `pyproject.toml` eliminates the need for `@pytest.mark.asyncio` on every test.
