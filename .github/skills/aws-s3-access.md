---
name: aws-s3-access
description: "Use when: reading objects from S3, listing bucket contents, creating an S3 client dependency, handling S3 errors (NoSuchKey, NoSuchBucket), or returning object content in a FastAPI response."
---

# AWS S3 Access

## When to use
- Implementing GET endpoints that read objects or list contents of an S3 bucket
- Setting up the boto3 S3 client as a FastAPI dependency
- Handling S3-specific exceptions and mapping them to HTTP errors

---

## Package and version

```
aioboto3>=13.0    # async boto3 wrapper
boto3>=1.38       # underlying SDK (installed as aioboto3 dependency)
```

Use `aioboto3` for async routes. Never call `boto3` sync methods directly inside an `async def` route — it blocks the event loop.

---

## S3 client dependency

```python
# src/s3/dependencies.py
from typing import Annotated, AsyncGenerator
import aioboto3
from fastapi import Depends
from src.config import settings

_session = aioboto3.Session()


async def get_s3_client():
    async with _session.client(
        "s3",
        region_name=settings.AWS_REGION,
        # Credentials are resolved automatically from environment /
        # IAM role — do NOT hardcode keys here.
    ) as client:
        yield client


S3ClientDep = Annotated[object, Depends(get_s3_client)]
```

> Credentials must come from the environment (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`),
> an IAM role, or `~/.aws/credentials`. **Never hardcode them.**

---

## Repository — core S3 operations

```python
# src/s3/repository.py
from typing import Any
import aioboto3
from botocore.exceptions import ClientError
from .exceptions import S3ObjectNotFound, S3BucketNotFound


async def list_objects(client, bucket: str) -> list[dict[str, Any]]:
    try:
        paginator = client.get_paginator("list_objects_v2")
        objects = []
        async for page in paginator.paginate(Bucket=bucket):
            objects.extend(page.get("Contents", []))
        return objects
    except ClientError as exc:
        _handle_client_error(exc, bucket=bucket)


async def get_object(client, bucket: str, key: str) -> dict[str, Any]:
    try:
        response = await client.get_object(Bucket=bucket, Key=key)
        body = await response["Body"].read()
        return {
            "content_type": response["ContentType"],
            "content_length": response["ContentLength"],
            "body": body,
        }
    except ClientError as exc:
        _handle_client_error(exc, bucket=bucket, key=key)


def _handle_client_error(exc: ClientError, bucket: str, key: str | None = None) -> None:
    code = exc.response["Error"]["Code"]
    if code == "NoSuchBucket":
        raise S3BucketNotFound(bucket)
    if code in ("NoSuchKey", "404"):
        raise S3ObjectNotFound(bucket, key)
    raise exc
```

---

## Domain exceptions → HTTP errors

```python
# src/s3/exceptions.py
from fastapi import HTTPException, status


class S3ObjectNotFound(HTTPException):
    def __init__(self, bucket: str, key: str | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{key}' not found in bucket '{bucket}'.",
        )


class S3BucketNotFound(HTTPException):
    def __init__(self, bucket: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bucket '{bucket}' does not exist or is not accessible.",
        )
```

---

## Service layer

```python
# src/s3/service.py
import base64
from .repository import list_objects as repo_list, get_object as repo_get
from .schemas import S3ObjectListResponse, S3ObjectMeta, S3ObjectResponse


class S3Service:
    def __init__(self, client) -> None:
        self._client = client

    async def list_objects(self, bucket: str) -> S3ObjectListResponse:
        raw = await repo_list(self._client, bucket)
        objects = [
            S3ObjectMeta(
                key=obj["Key"],
                size=obj["Size"],
                last_modified=obj["LastModified"],
                etag=obj["ETag"].strip('"'),
            )
            for obj in raw
        ]
        return S3ObjectListResponse(bucket=bucket, objects=objects, count=len(objects))

    async def get_object(self, bucket: str, key: str) -> S3ObjectResponse:
        raw = await repo_get(self._client, bucket, key)
        return S3ObjectResponse(
            bucket=bucket,
            key=key,
            content_type=raw["content_type"],
            body=base64.b64encode(raw["body"]).decode(),
            size=raw["content_length"],
        )
```

---

## Required environment variables

```ini
# .env
AWS_REGION=us-east-1
# Credentials (local dev only — use IAM roles in production)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

Add to `src/config.py`:

```python
class Settings(BaseSettings):
    AWS_REGION: str = "us-east-1"
    # Access key vars are read automatically by boto3; no need to forward them manually.
```

---

## Security rules

- Never log or return `AWS_SECRET_ACCESS_KEY` or session tokens.
- Restrict the IAM policy to `s3:GetObject` and `s3:ListBucket` on the specific bucket ARN — no `s3:*`.
- Use bucket policies + VPC endpoints in production to avoid public internet access.
- Validate the `bucket` path parameter against an allow-list if the bucket name comes from user input.
