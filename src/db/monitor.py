from datetime import datetime, timedelta
from typing import Any

from src.db.mysql import get_connection
from src.db.query import build_job_filters


def list_enabled_monitors() -> list[dict[str, Any]]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, user_id, name, company, city, keyword, job_type,
                    enabled, last_checked_at, created_at, updated_at
                FROM monitor_configs
                WHERE enabled = 1
                ORDER BY COALESCE(last_checked_at, '1970-01-01') ASC, id ASC
                """
            )
            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()


def create_monitor(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO monitor_configs (
                    user_id, name, company, city, keyword, job_type, enabled
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    data["name"].strip(),
                    data.get("company", "").strip(),
                    data.get("city", "").strip(),
                    data.get("keyword", "").strip(),
                    data.get("job_type", "").strip(),
                    1 if data.get("enabled", True) else 0,
                ),
            )
            monitor_id = cursor.lastrowid
        connection.commit()
        return get_monitor(user_id, monitor_id)
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def list_monitors(user_id: str) -> list[dict[str, Any]]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    m.id,
                    m.name,
                    m.company,
                    m.city,
                    m.keyword,
                    m.job_type,
                    m.enabled,
                    m.last_checked_at,
                    m.created_at,
                    m.updated_at,
                    COUNT(h.id) AS hit_count,
                    SUM(CASE WHEN h.notified_at IS NULL THEN 1 ELSE 0 END) AS pending_count
                FROM monitor_configs m
                LEFT JOIN monitor_hits h ON h.monitor_id = m.id
                WHERE m.user_id = %s
                GROUP BY m.id
                ORDER BY m.created_at DESC
                """,
                (user_id,),
            )
            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()


def get_monitor(user_id: str, monitor_id: int) -> dict[str, Any] | None:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id, name, company, city, keyword, job_type,
                    enabled, last_checked_at, created_at, updated_at
                FROM monitor_configs
                WHERE id = %s AND user_id = %s
                """,
                (monitor_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute(
                """
                SELECT COUNT(*) AS hit_count,
                       SUM(CASE WHEN notified_at IS NULL THEN 1 ELSE 0 END) AS pending_count
                FROM monitor_hits
                WHERE monitor_id = %s
                """,
                (monitor_id,),
            )
            stats = cursor.fetchone() or {}
            row["hit_count"] = int(stats.get("hit_count") or 0)
            row["pending_count"] = int(stats.get("pending_count") or 0)
            return row
    finally:
        if connection:
            connection.close()


def update_monitor(user_id: str, monitor_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    monitor = get_monitor(user_id, monitor_id)
    if monitor is None:
        return None

    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE monitor_configs
                SET name = %s,
                    company = %s,
                    city = %s,
                    keyword = %s,
                    job_type = %s,
                    enabled = %s
                WHERE id = %s AND user_id = %s
                """,
                (
                    data.get("name", monitor["name"]).strip(),
                    data.get("company", monitor["company"]).strip(),
                    data.get("city", monitor["city"]).strip(),
                    data.get("keyword", monitor["keyword"]).strip(),
                    data.get("job_type", monitor["job_type"]).strip(),
                    1 if data.get("enabled", bool(monitor["enabled"])) else 0,
                    monitor_id,
                    user_id,
                ),
            )
        connection.commit()
        return get_monitor(user_id, monitor_id)
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def delete_monitor(user_id: str, monitor_id: int) -> bool:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM monitor_configs WHERE id = %s AND user_id = %s",
                (monitor_id, user_id),
            )
        deleted = cursor.rowcount > 0
        connection.commit()
        return deleted
    finally:
        if connection:
            connection.close()


def find_matching_jobs(monitor: dict[str, Any], since: datetime | None) -> list[dict[str, Any]]:
    where_sql, params = build_job_filters(
        company=monitor.get("company"),
        city=monitor.get("city"),
        keyword=monitor.get("keyword"),
        job_type=monitor.get("job_type"),
    )

    if since is None:
        since = datetime.now() - timedelta(hours=24)

    if where_sql:
        where_sql += " AND (created_at > %s OR updated_at > %s)"
    else:
        where_sql = "WHERE (created_at > %s OR updated_at > %s)"
    params.extend([since, since])

    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    id, company, source, source_job_id, content_hash,
                    title, city, country, department, category,
                    salary, education, experience, description,
                    requirements, job_type, publish_time, update_time,
                    source_url, crawl_time, created_at, updated_at
                FROM jobs
                {where_sql}
                ORDER BY GREATEST(created_at, updated_at) ASC, id ASC
                LIMIT 100
                """,
                tuple(params),
            )
            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()


def record_hits(monitor_id: int, jobs: list[dict[str, Any]]) -> int:
    if not jobs:
        return 0

    connection = None
    inserted = 0
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            for job in jobs:
                cursor.execute(
                    """
                    INSERT IGNORE INTO monitor_hits (monitor_id, job_id)
                    VALUES (%s, %s)
                    """,
                    (monitor_id, job["id"]),
                )
                inserted += cursor.rowcount
        connection.commit()
        return inserted
    except Exception:
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def update_monitor_checked_at(monitor_id: int, checked_at: datetime | None = None) -> None:
    checked_at = checked_at or datetime.now()
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE monitor_configs SET last_checked_at = %s WHERE id = %s",
                (checked_at, monitor_id),
            )
        connection.commit()
    finally:
        if connection:
            connection.close()


def list_monitor_hits(user_id: str, monitor_id: int, limit: int = 50) -> list[dict[str, Any]]:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    h.id AS hit_id,
                    h.created_at AS hit_created_at,
                    h.notified_at,
                    j.id,
                    j.company,
                    j.title,
                    j.city,
                    j.department,
                    j.job_type,
                    j.update_time,
                    j.source_url
                FROM monitor_hits h
                INNER JOIN monitor_configs m ON m.id = h.monitor_id
                INNER JOIN jobs j ON j.id = h.job_id
                WHERE h.monitor_id = %s AND m.user_id = %s
                ORDER BY h.created_at DESC
                LIMIT %s
                """,
                (monitor_id, user_id, min(200, max(1, limit))),
            )
            return list(cursor.fetchall() or [])
    finally:
        if connection:
            connection.close()


def mark_hits_notified(user_id: str, monitor_id: int) -> int:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE monitor_hits h
                INNER JOIN monitor_configs m ON m.id = h.monitor_id
                SET h.notified_at = NOW()
                WHERE h.monitor_id = %s
                  AND m.user_id = %s
                  AND h.notified_at IS NULL
                """,
                (monitor_id, user_id),
            )
            count = cursor.rowcount
        connection.commit()
        return count
    finally:
        if connection:
            connection.close()
