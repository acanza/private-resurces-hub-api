import pytest
from httpx import AsyncClient

from src.resources.dependencies import valid_resource_id
from src.main import app


@pytest.fixture(autouse=True)
def _override_valid_resource():
    async def fake_resource(resource_id: str) -> dict:
        if resource_id == "existing-id":
            return {
                "id": "existing-id",
                "name": "Sample Resource",
                "s3_key": "resources/sample.pdf",
                "content_type": "application/pdf",
            }
        return None

    from src.resources import dependencies
    original = dependencies.valid_resource_id
    app.dependency_overrides[valid_resource_id] = fake_resource
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_resource_ok(client: AsyncClient):
    resp = await client.get("/resources/existing-id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "existing-id"
    assert data["name"] == "Sample Resource"


@pytest.mark.asyncio
async def test_get_resource_not_found(client: AsyncClient):
    resp = await client.get("/resources/nonexistent-id")
    assert resp.status_code == 404
