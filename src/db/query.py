from typing import Any

from src.db.mysql import get_connection


# =========================================================
# 构造岗位筛选条件
# =========================================================


def build_job_filters(
    company: str | None = None,
    city: str | None = None,
    keyword: str | None = None,
    job_type: str | None = None,
) -> tuple[str, list[Any]]:
    """根据查询参数生成安全的 SQL WHERE 子句和参数。"""

    conditions: list[str] = []
    params: list[Any] = []

    # 公司
    if company:
        company_value = company.strip()

        if company_value:
            conditions.append(
                "company LIKE %s"
            )
            params.append(
                f"%{company_value}%"
            )

    # 城市
    if city:
        city_value = city.strip()

        if city_value:
            conditions.append(
                "city LIKE %s"
            )
            params.append(
                f"%{city_value}%"
            )

    # 关键词
    if keyword:
        keyword_value = keyword.strip()

        if keyword_value:
            keyword_pattern = (
                f"%{keyword_value}%"
            )

            conditions.append(
                "("
                "title LIKE %s "
                "OR description LIKE %s "
                "OR requirements LIKE %s "
                "OR department LIKE %s "
                "OR category LIKE %s"
                ")"
            )

            params.extend(
                [keyword_pattern] * 5
            )

    # 岗位类型
    if job_type:
        job_type_value = job_type.strip()

        if job_type_value:
            conditions.append(
                "job_type LIKE %s"
            )
            params.append(
                f"%{job_type_value}%"
            )

    if not conditions:
        return "", params

    return (
        "WHERE " + " AND ".join(conditions),
        params,
    )


# =========================================================
# 构造岗位排序
# =========================================================


def build_job_order(
    sort_order: str = "latest",
) -> str:
    """
    构造安全的 SQL ORDER BY。

    latest:
        最新更新在前

    earliest:
        最早更新在前

    注意：
    sort_order 不能直接拼接进 SQL，
    只允许程序预先定义好的两种排序方式。
    """

    if sort_order == "earliest":
        return (
            "ORDER BY "
            "update_time ASC, "
            "crawl_time ASC, "
            "id ASC"
        )

    # 默认：最新更新
    return (
        "ORDER BY "
        "update_time DESC, "
        "crawl_time DESC, "
        "id DESC"
    )


# =========================================================
# 查询岗位列表
# =========================================================


def list_jobs(
    *,
    company: str | None = None,
    city: str | None = None,
    keyword: str | None = None,
    job_type: str | None = None,
    sort_order: str = "latest",
    page: int = 1,
    page_size: int = 20,
    user_id: str = "default",
) -> tuple[list[dict[str, Any]], int]:
    """
    查询岗位列表，同时返回总记录数。

    支持：
    - 公司筛选
    - 城市筛选
    - 关键词搜索
    - 岗位类型筛选
    - 最新/最早更新时间排序
    - 分页
    """

    # -----------------------------------------------------
    # 防止异常分页参数
    # -----------------------------------------------------

    page = max(1, page)
    page_size = max(1, min(100, page_size))

    # -----------------------------------------------------
    # 构造 WHERE
    # -----------------------------------------------------

    where_sql, params = build_job_filters(
        company=company,
        city=city,
        keyword=keyword,
        job_type=job_type,
    )

    # -----------------------------------------------------
    # 构造 ORDER BY
    # -----------------------------------------------------

    order_sql = build_job_order(
        sort_order=sort_order
    )

    # -----------------------------------------------------
    # 计算分页
    # -----------------------------------------------------

    offset = (page - 1) * page_size

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            # =================================================
            # 1. 查询符合条件的岗位总数
            # =================================================

            count_sql = (
                "SELECT COUNT(*) AS total "
                "FROM jobs "
                f"{where_sql}"
            )

            cursor.execute(
                count_sql,
                tuple(params),
            )

            total_row = (
                cursor.fetchone()
                or {"total": 0}
            )

            total = int(
                total_row["total"]
            )

            # =================================================
            # 2. 查询当前页
            # =================================================

            favorite_join = """
                LEFT JOIN favorites f
                    ON f.job_id = jobs.id
                   AND f.user_id = %s
            """

            list_sql = f"""
                SELECT
                    jobs.id,
                    jobs.company,
                    jobs.source,
                    jobs.source_job_id,
                    jobs.content_hash,
                    jobs.title,
                    jobs.city,
                    jobs.country,
                    jobs.department,
                    jobs.category,
                    jobs.salary,
                    jobs.education,
                    jobs.experience,
                    jobs.description,
                    jobs.requirements,
                    jobs.job_type,
                    jobs.publish_time,
                    jobs.update_time,
                    jobs.source_url,
                    jobs.crawl_time,
                    jobs.created_at,
                    jobs.updated_at,
                    CASE WHEN f.id IS NULL THEN FALSE ELSE TRUE END AS is_favorite
                FROM jobs
                {favorite_join}
                {where_sql}
                {order_sql}
                LIMIT %s OFFSET %s
            """

            cursor.execute(
                list_sql,
                tuple([user_id] + params)
                + (page_size, offset),
            )

            rows = cursor.fetchall() or []

        return rows, total

    finally:
        if connection:
            connection.close()


# =========================================================
# 查询单条岗位
# =========================================================


def get_job_by_id(
    job_id: int,
    user_id: str = "default",
) -> dict[str, Any] | None:
    """根据数据库主键查询岗位。"""

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    jobs.id,
                    jobs.company,
                    jobs.source,
                    jobs.source_job_id,
                    jobs.content_hash,
                    jobs.title,
                    jobs.city,
                    jobs.country,
                    jobs.department,
                    jobs.category,
                    jobs.salary,
                    jobs.education,
                    jobs.experience,
                    jobs.description,
                    jobs.requirements,
                    jobs.job_type,
                    jobs.publish_time,
                    jobs.update_time,
                    jobs.source_url,
                    jobs.crawl_time,
                    jobs.created_at,
                    jobs.updated_at,
                    CASE WHEN f.id IS NULL THEN FALSE ELSE TRUE END AS is_favorite
                FROM jobs
                LEFT JOIN favorites f
                    ON f.job_id = jobs.id
                   AND f.user_id = %s
                WHERE jobs.id = %s
                """,
                (user_id, job_id),
            )

            return cursor.fetchone()

    finally:
        if connection:
            connection.close()


# =========================================================
# 查询公司列表
# =========================================================


def list_companies() -> list[str]:
    """返回数据库中目前存在的公司名称。"""

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT company
                FROM jobs
                WHERE company IS NOT NULL
                  AND company <> ''
                GROUP BY company
                ORDER BY company
                """
            )

            rows = cursor.fetchall() or []

        return [
            row["company"]
            for row in rows
        ]

    finally:
        if connection:
            connection.close()
# =========================================================
# 查询城市列表
# =========================================================


def list_cities() -> list[str]:
    """返回数据库中目前存在的城市名称。"""

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT city
                FROM jobs
                WHERE city IS NOT NULL
                  AND city <> ''
                GROUP BY city
                ORDER BY city
                """
            )

            rows = cursor.fetchall() or []

        return [
            row["city"]
            for row in rows
        ]

    finally:
        if connection:
            connection.close()


# =========================================================
# 查询岗位类型列表
# =========================================================


def list_job_types() -> list[str]:
    """返回数据库中目前存在的岗位类型。"""

    connection = None

    try:
        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT job_type
                FROM jobs
                WHERE job_type IS NOT NULL
                  AND job_type <> ''
                GROUP BY job_type
                ORDER BY job_type
                """
            )

            rows = cursor.fetchall() or []

        return [
            row["job_type"]
            for row in rows
        ]

    finally:
        if connection:
            connection.close()