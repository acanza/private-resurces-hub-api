import pytest
from httpx import AsyncClient

from src.resources.dependencies import valid_category_access, valid_resource_id
from src.resources.exceptions import AccessDenied
from src.resources.schemas import CategoryAccessRequest
from src.main import app

FAKE_CF_COOKIES = {
    "CloudFront-Policy": "fake-policy",
    "CloudFront-Signature": "fake-sig",
    "CloudFront-Key-Pair-Id": "KPID123",
}

FAKE_CF_DOMAIN = "d123.cloudfront.net"


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


# ---------------------------------------------------------------------------
# POST /{category_id}/access
# ---------------------------------------------------------------------------


@pytest.fixture()
def _override_access_granted():
    async def fake_access(
        category_id: str, payload: CategoryAccessRequest
    ) -> CategoryAccessRequest:
        return payload

    app.dependency_overrides[valid_category_access] = fake_access
    yield
    app.dependency_overrides.pop(valid_category_access, None)


@pytest.fixture()
def _override_access_denied():
    async def fake_access(
        category_id: str, payload: CategoryAccessRequest
    ) -> CategoryAccessRequest:
        raise AccessDenied()

    app.dependency_overrides[valid_category_access] = fake_access
    yield
    app.dependency_overrides.pop(valid_category_access, None)


@pytest.mark.asyncio
async def test_request_category_access_ok(
    client: AsyncClient, _override_access_granted, monkeypatch
):
    from src.resources import service
    from src.resources.service import CloudFrontCookies
    import time

    fake_expires = int(time.time()) + 3600

    monkeypatch.setattr(
        service,
        "build_cloudfront_signed_cookies",
        lambda cat_id: CloudFrontCookies(cookies=FAKE_CF_COOKIES, expires_at=fake_expires),
    )
    monkeypatch.setattr(
        service.resources_settings,
        "CF_DISTRIBUTION_DOMAIN",
        FAKE_CF_DOMAIN,
    )

    resp = await client.post(
        "/resources/marketing/access",
        json={"email": "user@example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["cloudfront_url"] == f"https://{FAKE_CF_DOMAIN}/marketing/"
    assert body["expires_at"] == fake_expires

    set_cookies = resp.headers.get_list("set-cookie")
    cookie_names = {c.split("=")[0] for c in set_cookies}
    assert "CloudFront-Policy" in cookie_names
    assert "CloudFront-Signature" in cookie_names
    assert "CloudFront-Key-Pair-Id" in cookie_names


@pytest.mark.asyncio
async def test_request_category_access_forbidden(
    client: AsyncClient, _override_access_denied
):
    resp = await client.post(
        "/resources/marketing/access",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_request_category_access_invalid_email(
    client: AsyncClient, _override_access_granted
):
    resp = await client.post(
        "/resources/marketing/access",
        json={"email": "not-an-email"},
    )
    assert resp.status_code == 422
