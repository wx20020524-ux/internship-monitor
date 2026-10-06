from datetime import datetime

from pydantic import BaseModel, Field


class JobResponse(BaseModel):
    id: int
    company: str = ""
    source: str = ""
    source_job_id: str = ""
    content_hash: str = ""
    title: str = ""
    city: str = ""
    country: str = ""
    department: str = ""
    category: str = ""
    salary: str = ""
    education: str = ""
    experience: str = ""
    description: str = ""
    requirements: str = ""
    job_type: str = ""
    publish_time: str = ""
    update_time: str = ""
    source_url: str = ""
    crawl_time: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_favorite: bool = False


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobResponse] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str = "disabled"


class FavoriteResponse(BaseModel):
    job_id: int
    is_favorite: bool


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str = ""
    city: str = ""
    keyword: str = ""
    job_type: str = ""
    enabled: bool = True


class MonitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = None
    city: str | None = None
    keyword: str | None = None
    job_type: str | None = None
    enabled: bool | None = None


class MonitorResponse(BaseModel):
    id: int
    name: str
    company: str = ""
    city: str = ""
    keyword: str = ""
    job_type: str = ""
    enabled: bool
    last_checked_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    hit_count: int = 0
    pending_count: int = 0


class MonitorRunResponse(BaseModel):
    monitor_id: int
    new_hits: int
    jobs: list[dict] = Field(default_factory=list)


class EmbeddingIndexRequest(BaseModel):
    limit: int = Field(default=200, ge=1, le=5000)


class EmbeddingIndexResponse(BaseModel):
    requested: int
    indexed: int
    skipped: int


class EmbeddingStatusResponse(BaseModel):
    model: str
    dimension: int
    indexed_jobs: int
    total_jobs: int
