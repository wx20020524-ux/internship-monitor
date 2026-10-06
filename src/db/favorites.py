from typing import Any

from src.db.mysql import get_connection


def add_favorite(user_id: str, job_id: int) -> dict[str, Any]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM jobs WHERE id = %s", (job_id,))
            if cursor.fetchone() is None:
                raise ValueError("岗位不存在")

            cursor.execute(
                """
                INSERT INTO favorites (user_id, job_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE created_at = created_at
                """,
                (user_id, job_id),
            )
        connection.commit()
        return {"job_id": job_id, "is_favorite": True}
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def remove_favorite(user_id: str, job_id: int) -> dict[str, Any]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM favorites WHERE user_id = %s AND job_id = %s",
                (user_id, job_id),
            )
        connection.commit()
        return {"job_id": job_id, "is_favorite": False}
    finally:
        if connection:
            connection.close()


def is_favorite(user_id: str, job_id: int) -> bool:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM favorites WHERE user_id = %s AND job_id = %s LIMIT 1",
                (user_id, job_id),
            )
            return cursor.fetchone() is not None
    finally:
        if connection:
            connection.close()


def list_favorites(user_id: str) -> list[dict[str, Any]]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    j.id,
                    j.company,
                    j.source,
                    j.source_job_id,
                    j.content_hash,
                    j.title,
                    j.city,
                    j.country,
                    j.department,
                    j.category,
                    j.salary,
                    j.education,
                    j.experience,
                    j.description,
                    j.requirements,
                    j.job_type,
                    j.publish_time,
                    j.update_time,
                    j.source_url,
                    j.crawl_time,
                    j.created_at,
                    j.updated_at,
                    TRUE AS is_favorite,
                    f.created_at AS favorite_created_at
                FROM favorites f
                INNER JOIN jobs j ON j.id = f.job_id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
                """,
                (user_id,),
            )
            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()
