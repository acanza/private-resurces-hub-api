from pydantic import BaseModel, EmailStr, Field


class ResourceResponse(BaseModel):
    id: str
    name: str
    s3_key: str
    content_type: str | None = None


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    content_type: str | None = None


class CategoryAccessRequest(BaseModel):
    email: EmailStr


class CategoryAccessResponse(BaseModel):
    cloudfront_url: str
    expires_at: int


class ResourceItemResponse(BaseModel):
    name: str
    has_access: bool
    access_url: str | None = None


class ResourceListResponse(BaseModel):
    resources: list[ResourceItemResponse]
