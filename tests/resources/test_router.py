import pytest
from httpx import AsyncClient

from src.main import app
from src.resources.dependencies import valid_category_access
from src.resources.exceptions import AccessDeniedError
from src.resources.schemas import CategoryAccessRequest

FAKE_CF_COOKIES = {
    "CloudFront-Policy": "fake-policy",
    "CloudFront-Signature": "fake-sig",
    "CloudFront-Key-Pair-Id": "KPID123",
}

FAKE_CF_DOMAIN = "d123.cloudfront.net"


# ---------------------------------------------------------------------------
# GET /{category_id}
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
        raise AccessDeniedError()

    app.dependency_overrides[valid_category_access] = fake_access
    yield
    app.dependency_overrides.pop(valid_category_access, None)


@pytest.mark.asyncio
async def test_get_category_items_ok(
    client: AsyncClient, _override_access_granted, monkeypatch
):
    from src.resources import service

    async def fake_list_items(email: str, category_id: str) -> list[dict]:
        return [
            {
                "name": "item-a.pdf",
                "signed_url": "https://d123.cloudfront.net/tech/item-a.pdf?Policy=...",
            },
            {
                "name": "item-b.txt",
                "signed_url": "https://d123.cloudfront.net/tech/item-b.txt?Policy=...",
            },
        ]

    monkeypatch.setattr(
        service, "list_category_items_with_signed_urls", fake_list_items
    )

    resp = await client.get(
        "/resources/tech",
        json={"email": "user@example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "item-a.pdf"
    assert "signed_url" in body["items"][0]
    assert body["items"][1]["name"] == "item-b.txt"


@pytest.mark.asyncio
async def test_get_category_items_empty(
    client: AsyncClient, _override_access_granted, monkeypatch
):
    from src.resources import service

    async def fake_list_items(email: str, category_id: str) -> list[dict]:
        return []

    monkeypatch.setattr(
        service, "list_category_items_with_signed_urls", fake_list_items
    )

    resp = await client.get(
        "/resources/empty-category",
        json={"email": "user@example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


@pytest.mark.asyncio
async def test_get_category_items_forbidden(
    client: AsyncClient, _override_access_denied
):
    resp = await client.get(
        "/resources/restricted",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "ACCESS_DENIED"


# ---------------------------------------------------------------------------
# POST /{category_id}/access
# ---------------------------------------------------------------------------


@pytest.fixture()
def _override_access_granted_post():
    async def fake_access(
        category_id: str, payload: CategoryAccessRequest
    ) -> CategoryAccessRequest:
        return payload

    app.dependency_overrides[valid_category_access] = fake_access
    yield
    app.dependency_overrides.pop(valid_category_access, None)


@pytest.fixture()
def _override_access_denied_post():
    async def fake_access(
        category_id: str, payload: CategoryAccessRequest
    ) -> CategoryAccessRequest:
        raise AccessDeniedError()

    app.dependency_overrides[valid_category_access] = fake_access
    yield
    app.dependency_overrides.pop(valid_category_access, None)


@pytest.mark.asyncio
async def test_request_category_access_ok(
    client: AsyncClient, _override_access_granted_post, monkeypatch
):
    import time

    from src.resources import service
    from src.resources.service import CloudFrontCookies

    fake_expires = int(time.time()) + 3600

    async def fake_build(cat_id: str) -> CloudFrontCookies:
        return CloudFrontCookies(cookies=FAKE_CF_COOKIES, expires_at=fake_expires)

    monkeypatch.setattr(service, "build_cloudfront_signed_cookies", fake_build)
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
    client: AsyncClient, _override_access_denied_post
):
    resp = await client.post(
        "/resources/marketing/access",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_request_category_access_invalid_email(
    client: AsyncClient, _override_access_granted_post
):
    resp = await client.post(
        "/resources/marketing/access",
        json={"email": "not-an-email"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_resources_ok(client: AsyncClient, monkeypatch):
    from src.resources import service

    async def fake_list_resources(email: str) -> list[dict]:
        return [
            {
                "name": "tech",
                "has_access": True,
                "access_url": "/resources/tech/access",
            },
            {"name": "finance", "has_access": False, "access_url": None},
            {"name": "hr", "has_access": True, "access_url": "/resources/hr/access"},
        ]

    monkeypatch.setattr(service, "list_resources_with_access", fake_list_resources)

    resp = await client.post(
        "/resources/",
        json={"email": "user@example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "resources" in body
    assert len(body["resources"]) == 3

    # Check first resource (with access)
    assert body["resources"][0]["name"] == "tech"
    assert body["resources"][0]["has_access"] is True
    assert body["resources"][0]["access_url"] == "/resources/tech/access"

    # Check second resource (without access)
    assert body["resources"][1]["name"] == "finance"
    assert body["resources"][1]["has_access"] is False
    assert body["resources"][1]["access_url"] is None

    # Check third resource (with access)
    assert body["resources"][2]["name"] == "hr"
    assert body["resources"][2]["has_access"] is True
    assert body["resources"][2]["access_url"] == "/resources/hr/access"


@pytest.mark.asyncio
async def test_list_resources_empty(client: AsyncClient, monkeypatch):
    from src.resources import service

    async def fake_list_resources(email: str) -> list[dict]:
        return []

    monkeypatch.setattr(service, "list_resources_with_access", fake_list_resources)

    resp = await client.post(
        "/resources/",
        json={"email": "user@example.com"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["resources"] == []


@pytest.mark.asyncio
async def test_list_resources_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/resources/",
        json={"email": "not-an-email"},
    )
    assert resp.status_code == 422
