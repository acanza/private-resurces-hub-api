import base64
import json
import time
from dataclasses import dataclass

import aioboto3
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from src.resources.config import resources_settings
from src.resources.exceptions import (
    CloudFrontSigningError,
    DynamoDBAccessError,
    S3AccessError,
)

_cf_private_key_cache: str | None = None


async def _get_cf_private_key() -> str:
    global _cf_private_key_cache
    if _cf_private_key_cache is None:
        session = aioboto3.Session()
        async with session.client(
            "secretsmanager", region_name=resources_settings.REGION
        ) as client:
            response = await client.get_secret_value(
                SecretId=resources_settings.CF_SECRET_NAME
            )
            _cf_private_key_cache = response["SecretString"]
    return _cf_private_key_cache


async def get_resource(resource_id: str) -> dict | None:
    session = aioboto3.Session()
    try:
        async with session.resource(
            "dynamodb", region_name=resources_settings.REGION
        ) as dynamodb:
            table = await dynamodb.Table(resources_settings.DYNAMODB_TABLE)
            response = await table.get_item(Key={"pk": resource_id, "sk": "METADATA"})
            item = response.get("Item")
            if not item:
                return None
            return {
                "id": resource_id,
                "name": item["name"],
                "s3_key": item["s3_key"],
                "content_type": item.get("content_type"),
            }
    except ClientError as exc:
        raise DynamoDBAccessError() from exc


async def check_user_access(email: str, category_id: str) -> bool:
    session = aioboto3.Session()
    try:
        async with session.resource(
            "dynamodb", region_name=resources_settings.REGION
        ) as dynamodb:
            table = await dynamodb.Table(resources_settings.DYNAMODB_TABLE)
            response = await table.get_item(
                Key={"pk": email, "sk": f"RESOURCE#{category_id}"}
            )
            return "Item" in response
    except ClientError as exc:
        raise DynamoDBAccessError() from exc


async def list_resources_with_access(
    email: str,
) -> list[dict[str, str | bool | None]]:
    """List all S3 directories and check user access permissions."""
    session = aioboto3.Session()
    try:
        # Get all directories from S3
        async with session.client(
            "s3", region_name=resources_settings.REGION
        ) as s3_client:
            response = await s3_client.list_objects_v2(
                Bucket=resources_settings.S3_BUCKET,
                Delimiter="/",
            )

        directories = []
        # Process common prefixes (directories)
        if "CommonPrefixes" in response:
            for prefix_info in response["CommonPrefixes"]:
                prefix = prefix_info["Prefix"]
                # Remove trailing slash to get directory name
                directory_name = prefix.rstrip("/")

                # Check if user has access to this directory
                has_access = await check_user_access(email, directory_name)

                resource_item = {
                    "name": directory_name,
                    "has_access": has_access,
                    "access_url": (
                        f"/resources/{directory_name}/access" if has_access else None
                    ),
                }
                directories.append(resource_item)

        return directories
    except ClientError as exc:
        raise S3AccessError() from exc


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


async def build_cloudfront_signed_cookies(category_id: str) -> CloudFrontCookies:
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
        private_key_pem = await _get_cf_private_key()
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
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
