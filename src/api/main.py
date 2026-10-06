from fastapi import FastAPI, HTTPException, Header, Query

from src.ai.resume_api import router as resume_router
from src.api.ai import router as ai_router
from src.api.favorites import router as favorite_router
from src.api.monitors import router as monitor_router
from src.api.schemas import HealthResponse, JobListResponse, JobResponse
from src.cache.redis import cache
from src.db.favorites import is_favorite
from src.db.mysql import get_connection
from src.db.query import list_cities, list_companies, list_job_types, list_jobs, get_job_by_id
from src.db.schema import ensure_schema


app = FastAPI(
    title="AI 实时实习信息平台",
    description="查询腾讯、字节跳动等公司岗位，并提供简历智能匹配、收藏和岗位监控。",
    version="2.0.0",
)

app.include_router(resume_router)
app.include_router(favorite_router)
app.include_router(monitor_router)
app.include_router(ai_router)


@app.on_event("startup")
def startup() -> None:
    ensure_schema()


@app.get("/health", response_model=HealthResponse, tags=["系统"])
def health_check() -> HealthResponse:
    connection = None
    database = "error"
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        database = "ok"
    except Exception:
        pass
    finally:
        if connection:
            connection.close()
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        database=database,
        redis="ok" if cache.available else "unavailable",
    )


@app.get("/companies", response_model=list[str], tags=["岗位查询"])
def companies():
    cached = cache.get_json("job-options:companies")
    if isinstance(cached, list):
        return cached
    data = list_companies()
    cache.set_json("job-options:companies", data, ttl=300)
    return data


@app.get("/cities", response_model=list[str], tags=["岗位查询"])
def cities():
    cached = cache.get_json("job-options:cities")
    if isinstance(cached, list):
        return cached
    data = list_cities()
    cache.set_json("job-options:cities", data, ttl=300)
    return data


@app.get("/job-types", response_model=list[str], tags=["岗位查询"])
def job_types():
    cached = cache.get_json("job-options:job-types")
    if isinstance(cached, list):
        return cached
    data = list_job_types()
    cache.set_json("job-options:job-types", data, ttl=300)
    return data


@app.get("/jobs", response_model=JobListResponse, tags=["岗位查询"])
def jobs(
    company: str | None = Query(default=None),
    city: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    sort_order: str = Query(default="latest", pattern="^(latest|earliest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    x_user_id: str | None = Header(default=None),
):
    user_id = (x_user_id or "default").strip()[:100] or "default"
    rows, total = list_jobs(
        company=company,
        city=city,
        keyword=keyword,
        job_type=job_type,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        user_id=user_id,
    )
    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[JobResponse.model_validate(row) for row in rows],
    )


@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["岗位查询"])
def job_detail(job_id: int, x_user_id: str | None = Header(default=None)):
    user_id = (x_user_id or "default").strip()[:100] or "default"
    row = get_job_by_id(job_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return JobResponse.model_validate(row)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=False)
