from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    id: str
    name: str
    s3_key: str
    content_type: str | None = None


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    content_type: str | None = None
