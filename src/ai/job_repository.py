from typing import Any

from src.db.mysql import get_connection


class JobRepository:
    """从 MySQL jobs 表读取岗位。"""

    def get_jobs(self, limit: int = 2000) -> list[dict[str, Any]]:
        connection = None
        try:
            connection = get_connection()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        company,
                        source,
                        source_job_id,
                        content_hash,
                        title,
                        city,
                        country,
                        department,
                        category,
                        salary,
                        education,
                        experience,
                        description,
                        requirements,
                        job_type,
                        publish_time,
                        update_time,
                        source_url,
                        crawl_time,
                        created_at,
                        updated_at
                    FROM jobs
                    ORDER BY update_time DESC, id DESC
                    LIMIT %s
                    """,
                    (max(1, min(10000, limit)),),
                )
                return list(cursor.fetchall() or [])
        finally:
            if connection:
                connection.close()
