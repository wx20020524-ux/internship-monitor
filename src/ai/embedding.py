import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from src.ai.job_repository import JobRepository
from src.ai.resume_schema import ResumeProfile
from src.db.mysql import get_connection

load_dotenv()


# =========================
# Embedding 配置
# =========================

EMBEDDING_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
EMBEDDING_API_KEY = os.getenv("LLM_API_KEY", "").strip()

# 百炼 Embedding 模型
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-v4",
).strip()

# 向量维度
EMBEDDING_DIMENSION = int(
    os.getenv("EMBEDDING_DIMENSION", "1024")
)


# =========================
# 岗位文本构造
# =========================

def job_to_text(job: dict[str, Any]) -> str:
    """
    将岗位结构化字段拼接成 Embedding 输入文本。
    """

    return "\n".join(
        [
            f"公司：{job.get('company', '')}",
            f"岗位：{job.get('title', '')}",
            f"城市：{job.get('city', '')}",
            f"部门：{job.get('department', '')}",
            f"类别：{job.get('category', '')}",
            f"岗位类型：{job.get('job_type', '')}",
            f"学历：{job.get('education', '')}",
            f"经验：{job.get('experience', '')}",
            f"岗位描述：{job.get('description', '')}",
            f"岗位要求：{job.get('requirements', '')}",
        ]
    )


def profile_to_text(profile: ResumeProfile) -> str:
    """
    将 ResumeProfile 转换为 Embedding 输入文本。
    """

    return "\n".join(
        [
            f"教育：{profile.education}",
            f"技能：{'、'.join(profile.skills)}",
            f"项目：{'；'.join(profile.projects)}",
            f"经历：{'；'.join(profile.experience)}",
            f"目标岗位：{'、'.join(profile.target_roles)}",
        ]
    )


# =========================
# Embedding API Client
# =========================

class EmbeddingClient:
    """
    调用百炼 OpenAI-compatible Embedding API。
    """

    # 百炼 text-embedding-v4 单次最多 10 条输入
    MAX_BATCH_SIZE = 10

    def __init__(self) -> None:
        self.base_url = EMBEDDING_BASE_URL
        self.api_key = EMBEDDING_API_KEY
        self.model = EMBEDDING_MODEL
        self.dimension = EMBEDDING_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成 Embedding。

        注意：
        text-embedding-v4 单次最多 10 条输入。
        """

        if not self.base_url:
            raise ValueError(
                "未配置 LLM_BASE_URL，无法生成 Embedding"
            )

        if not self.api_key:
            raise ValueError(
                "未配置 LLM_API_KEY，无法生成 Embedding"
            )

        if not texts:
            return []

        # 额外保护：
        # 即使调用方错误地传入超过 10 条，
        # 这里也不会直接发出非法请求。
        if len(texts) > self.MAX_BATCH_SIZE:
            raise ValueError(
                f"Embedding 单次最多支持 "
                f"{self.MAX_BATCH_SIZE} 条文本，"
                f"当前收到 {len(texts)} 条"
            )

        url = f"{self.base_url}/embeddings"

        payload: dict[str, Any] = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }

        if self.dimension:
            payload["dimensions"] = self.dimension

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            response.raise_for_status()

            data = response.json()

        except httpx.HTTPStatusError as error:
            raise RuntimeError(
                f"Embedding API 请求失败："
                f"HTTP {error.response.status_code}\n"
                f"响应内容：{error.response.text}"
            ) from error

        except httpx.RequestError as error:
            raise RuntimeError(
                f"Embedding 网络请求失败：{error}"
            ) from error

        items = data.get("data") or []

        # 按 index 排序，保证返回向量和输入文本顺序一致
        items.sort(
            key=lambda item: item.get("index", 0)
        )

        vectors = [
            item.get("embedding")
            for item in items
        ]

        if (
            len(vectors) != len(texts)
            or any(not isinstance(v, list) for v in vectors)
        ):
            raise RuntimeError(
                f"Embedding 返回数量异常：{data}"
            )

        return vectors


# =========================
# Embedding Repository
# =========================

class EmbeddingRepository:
    """
    将岗位 Embedding 向量保存到 MySQL。
    """

    def upsert(
        self,
        job_id: int,
        content_hash: str,
        vector: list[float],
    ) -> None:

        connection = None

        try:
            connection = get_connection()

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    INSERT INTO job_embeddings (
                        job_id,
                        model,
                        dimension,
                        content_hash,
                        embedding
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON DUPLICATE KEY UPDATE
                        model = VALUES(model),
                        dimension = VALUES(dimension),
                        content_hash = VALUES(content_hash),
                        embedding = VALUES(embedding),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        job_id,
                        EMBEDDING_MODEL,
                        len(vector),
                        content_hash,
                        json.dumps(
                            vector,
                            ensure_ascii=False,
                        ),
                    ),
                )

            connection.commit()

        except Exception:

            if connection:
                connection.rollback()

            raise

        finally:

            if connection:
                connection.close()

    def get_valid_vectors(
        self,
        jobs: list[dict[str, Any]],
    ) -> dict[int, list[float]]:

        if not jobs:
            return {}

        job_ids = [
            int(job["id"])
            for job in jobs
            if job.get("id") is not None
        ]

        if not job_ids:
            return {}

        placeholders = ",".join(
            ["%s"] * len(job_ids)
        )

        connection = None

        try:
            connection = get_connection()

            with connection.cursor() as cursor:

                cursor.execute(
                    f"""
                    SELECT
                        job_id,
                        content_hash,
                        embedding
                    FROM job_embeddings
                    WHERE model = %s
                      AND job_id IN ({placeholders})
                    """,
                    tuple(
                        [EMBEDDING_MODEL] + job_ids
                    ),
                )

                rows = cursor.fetchall() or []

            expected_hash = {
                int(job["id"]): job.get(
                    "content_hash",
                    "",
                )
                for job in jobs
            }

            result: dict[int, list[float]] = {}

            for row in rows:

                job_id = int(
                    row["job_id"]
                )

                # 岗位发生变化后，旧向量不能继续使用
                if (
                    row.get("content_hash")
                    != expected_hash.get(job_id)
                ):
                    continue

                try:

                    vector = json.loads(
                        row["embedding"]
                    )

                    if isinstance(vector, list):
                        result[job_id] = vector

                except (
                    TypeError,
                    json.JSONDecodeError,
                ):
                    continue

            return result

        finally:

            if connection:
                connection.close()


# =========================
# Embedding Matcher
# =========================

class EmbeddingMatcher:

    def __init__(self) -> None:

        self.client = EmbeddingClient()

        self.repository = EmbeddingRepository()

    # =========================
    # 建立岗位 Embedding 索引
    # =========================

    def index_jobs(
        self,
        limit: int = 200,
        batch_size: int = 10,
    ) -> dict[str, int]:
        """
        为岗位建立 Embedding 索引。

        重要：
        百炼 text-embedding-v4 单次最多 10 条输入，
        因此这里强制把 batch_size 限制在 1~10。
        """

        # =========================
        # 防止 batch_size 超过 API 限制
        # =========================

        batch_size = min(
            max(1, batch_size),
            EmbeddingClient.MAX_BATCH_SIZE,
        )

        repository = JobRepository()

        jobs = repository.get_jobs(
            limit=max(
                1,
                min(5000, limit),
            )
        )

        created = 0
        skipped = 0

        # =========================
        # 分批处理
        # =========================

        for start in range(
            0,
            len(jobs),
            batch_size,
        ):

            batch = jobs[
                start:start + batch_size
            ]

            # 只处理有数据库 ID 和 content_hash 的岗位
            valid = [
                job
                for job in batch
                if (
                    job.get("id")
                    and job.get("content_hash")
                )
            ]

            if not valid:

                skipped += len(batch)

                continue

            # =========================
            # 调用 Embedding API
            # =========================

            texts = [
                job_to_text(job)
                for job in valid
            ]

            vectors = self.client.embed(
                texts
            )

            # =========================
            # 保存向量
            # =========================

            for job, vector in zip(
                valid,
                vectors,
            ):

                self.repository.upsert(
                    job["id"],
                    job["content_hash"],
                    vector,
                )

                created += 1

        return {
            "requested": len(jobs),
            "indexed": created,
            "skipped": skipped,
        }

    # =========================
    # 余弦相似度
    # =========================

    @staticmethod
    def cosine_similarity(
        a: list[float],
        b: list[float],
    ) -> float:

        # 向量为空或者维度不一致
        if (
            not a
            or not b
            or len(a) != len(b)
        ):
            return 0.0

        dot = sum(
            x * y
            for x, y in zip(a, b)
        )

        norm_a = sum(
            x * x
            for x in a
        ) ** 0.5

        norm_b = sum(
            y * y
            for y in b
        ) ** 0.5

        if (
            norm_a == 0
            or norm_b == 0
        ):
            return 0.0

        return dot / (
            norm_a * norm_b
        )

    # =========================
    # 语义召回
    # =========================

    def semantic_rank(
        self,
        profile: ResumeProfile,
        jobs: list[dict[str, Any]],
        top_k: int = 20,
    ) -> tuple[list[dict[str, Any]], bool]:
        """
        根据简历向量和岗位向量计算语义相似度。
        """

        vectors = self.repository.get_valid_vectors(
            jobs
        )

        # 没有有效岗位向量
        if not vectors:
            return [], False

        # =========================
        # 简历只需要调用一次 Embedding
        # =========================

        profile_vector = self.client.embed(
            [
                profile_to_text(profile)
            ]
        )[0]

        scored = []

        for job in jobs:

            job_id = job.get("id")

            if job_id is None:
                continue

            vector = vectors.get(
                int(job_id)
            )

            if vector is None:
                continue

            similarity = self.cosine_similarity(
                profile_vector,
                vector,
            )

            scored.append(
                {
                    "job": job,
                    "semantic_score": round(
                        similarity * 100,
                        2,
                    ),
                }
            )

        # 相似度从高到低排序
        scored.sort(
            key=lambda item: item["semantic_score"],
            reverse=True,
        )

        return (
            scored[:top_k],
            True,
        )