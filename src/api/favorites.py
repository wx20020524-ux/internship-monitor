from fastapi import APIRouter, Header, HTTPException

from src.api.schemas import FavoriteResponse, JobResponse
from src.db.favorites import add_favorite, is_favorite, list_favorites, remove_favorite
from src.db.query import get_job_by_id


router = APIRouter(prefix="/favorites", tags=["收藏"])


def _user_id(x_user_id: str | None) -> str:
    value = (x_user_id or "default").strip()
    return value[:100] or "default"


@router.get("", response_model=list[JobResponse])
def favorites(x_user_id: str | None = Header(default=None)):
    return [JobResponse.model_validate(row) for row in list_favorites(_user_id(x_user_id))]


@router.post("/{job_id}", response_model=FavoriteResponse)
def create_favorite(job_id: int, x_user_id: str | None = Header(default=None)):
    try:
        return add_favorite(_user_id(x_user_id), job_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/{job_id}", response_model=FavoriteResponse)
def delete_favorite(job_id: int, x_user_id: str | None = Header(default=None)):
    return remove_favorite(_user_id(x_user_id), job_id)


@router.get("/{job_id}/status", response_model=FavoriteResponse)
def favorite_status(job_id: int, x_user_id: str | None = Header(default=None)):
    if get_job_by_id(job_id, _user_id(x_user_id)) is None:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {"job_id": job_id, "is_favorite": is_favorite(_user_id(x_user_id), job_id)}
