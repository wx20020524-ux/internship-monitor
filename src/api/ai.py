import os

from fastapi import APIRouter, HTTPException

from src.ai.embedding import EMBEDDING_DIMENSION, EMBEDDING_MODEL, EmbeddingMatcher
from src.api.schemas import EmbeddingIndexRequest, EmbeddingIndexResponse, EmbeddingStatusResponse
from src.db.mysql import get_connection


router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/embeddings/index", response_model=EmbeddingIndexResponse)
def build_embedding_index(payload: EmbeddingIndexRequest):
    try:
        return EmbeddingMatcher().index_jobs(limit=payload.limit)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"构建语义索引失败：{error}") from error


@router.get("/embeddings/status", response_model=EmbeddingStatusResponse)
def embedding_status():
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM jobs")
            total_jobs = int((cursor.fetchone() or {}).get("total", 0))
            cursor.execute(
                "SELECT COUNT(*) AS total FROM job_embeddings WHERE model = %s",
                (EMBEDDING_MODEL,),
            )
            indexed_jobs = int((cursor.fetchone() or {}).get("total", 0))
        return {
            "model": EMBEDDING_MODEL,
            "dimension": EMBEDDING_DIMENSION,
            "indexed_jobs": indexed_jobs,
            "total_jobs": total_jobs,
        }
    finally:
        if connection:
            connection.close()
