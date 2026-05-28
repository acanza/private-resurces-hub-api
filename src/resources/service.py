import base64
import json
import time
from dataclasses import dataclass

import aioboto3
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from src.resources.config import resources_settings
from src.resources.exceptions import CloudFrontSigningError, DynamoDBAccessError


async def get_resource(resource_id: str) -> dict | None:
    raise NotImplementedError


async def check_user_access(email: str, category_id: str) -> bool:
    session = aioboto3.Session()
    try:
        async with session.resource(
            "dynamodb", region_name=resources_settings.REGION
        ) as dynamodb:
            table = await dynamodb.Table(resources_settings.DYNAMODB_TABLE)
            response = await table.get_item(Key={"pk": email})
            item = response.get("Item")
            if not item:
                return False
            allowed: set[str] = item.get("allowed_categories", set())
            return category_id in allowed
    except ClientError as exc:
        raise DynamoDBAccessError() from exc


@dataclass
class CloudFrontCookies:
    cookies: dict[str, str]
    expires_at: int


def _cf_b64(data: bytes) -> str:
    return (
        base64.b64encode(data)
        .decode()
        .replace("+", "-")
        .replace("=", "_")
        .replace("/", "~")
    )


def build_cloudfront_signed_cookies(category_id: str) -> CloudFrontCookies:
    expires_at = int(time.time()) + resources_settings.CF_COOKIE_MAX_AGE_SECONDS
    resource_url = (
        f"https://{resources_settings.CF_DISTRIBUTION_DOMAIN}/{category_id}/*"
    )
    policy = json.dumps(
        {
            "Statement": [
                {
                    "Resource": resource_url,
                    "Condition": {"DateLessThan": {"AWS:EpochTime": expires_at}},
                }
            ]
        },
        separators=(",", ":"),
    )
    try:
        private_key = serialization.load_pem_private_key(
            resources_settings.CF_PRIVATE_KEY.encode(),
            password=None,
        )
        signature_bytes = private_key.sign(  # noqa: S303
            policy.encode(),
            padding.PKCS1v15(),
            hashes.SHA1(),  # noqa: S303
        )
    except Exception as exc:
        raise CloudFrontSigningError() from exc

    return CloudFrontCookies(
        cookies={
            "CloudFront-Policy": _cf_b64(policy.encode()),
            "CloudFront-Signature": _cf_b64(signature_bytes),
            "CloudFront-Key-Pair-Id": resources_settings.CF_KEY_PAIR_ID,
        },
        expires_at=expires_at,
    )
