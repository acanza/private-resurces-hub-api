from pydantic import BaseModel, EmailStr


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


class CategoryItemResponse(BaseModel):
    name: str
    signed_url: str


class CategoryItemsResponse(BaseModel):
    items: list[CategoryItemResponse]
