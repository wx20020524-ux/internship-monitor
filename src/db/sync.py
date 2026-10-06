import json
from pathlib import Path

from src.db.mysql import get_connection
from src.models import Job


# =========================================================
# 项目根目录
# =========================================================

BASE_DIR = Path(
    __file__
).resolve().parents[2]


# =========================================================
# 从 JSON 加载岗位
# =========================================================

def load_jobs_from_json(
    json_path: str | Path,
) -> list[Job]:
    """
    从 JSON 文件读取岗位，
    并转换成 Job 对象。
    """

    json_path = Path(
        json_path
    )

    if not json_path.exists():

        raise FileNotFoundError(
            f"JSON 文件不存在：{json_path}"
        )

    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):

        raise ValueError(
            "JSON 数据格式错误："
            "根节点必须是岗位列表"
        )

    jobs = []

    for item in data:

        jobs.append(
            Job.model_validate(
                item
            )
        )

    return jobs


# =========================================================
# INSERT
# =========================================================

def insert_job(
    cursor,
    job: Job,
) -> None:
    """
    向 jobs 表插入一条新岗位。
    """

    sql = """
        INSERT INTO jobs (
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
            crawl_time
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
    """

    cursor.execute(
        sql,
        (
            job.company,
            job.source,
            job.source_job_id,
            job.content_hash,
            job.title,
            job.city,
            job.country,
            job.department,
            job.category,
            job.salary,
            job.education,
            job.experience,
            job.description,
            job.requirements,
            job.job_type,
            job.publish_time,
            job.update_time,
            job.source_url,
            job.crawl_time,
        ),
    )


# =========================================================
# UPDATE
# =========================================================

def update_job(
    cursor,
    job: Job,
) -> None:
    """
    更新数据库中已经存在，
    但内容发生变化的岗位。
    """

    sql = """
        UPDATE jobs
        SET
            company = %s,
            content_hash = %s,
            title = %s,
            city = %s,
            country = %s,
            department = %s,
            category = %s,
            salary = %s,
            education = %s,
            experience = %s,
            description = %s,
            requirements = %s,
            job_type = %s,
            publish_time = %s,
            update_time = %s,
            source_url = %s,
            crawl_time = %s
        WHERE
            source = %s
            AND source_job_id = %s
    """

    cursor.execute(
        sql,
        (
            job.company,
            job.content_hash,
            job.title,
            job.city,
            job.country,
            job.department,
            job.category,
            job.salary,
            job.education,
            job.experience,
            job.description,
            job.requirements,
            job.job_type,
            job.publish_time,
            job.update_time,
            job.source_url,
            job.crawl_time,
            job.source,
            job.source_job_id,
        ),
    )


# =========================================================
# 同步岗位
# =========================================================

def sync_jobs(
    jobs: list[Job],
) -> dict[str, int]:
    """
    将岗位同步到 MySQL。

    返回：

        inserted
            新增数量

        updated
            更新数量

        unchanged
            内容没有变化数量

        skipped
            缺少 source_job_id 而跳过的数量
    """

    connection = None

    stats = {
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
    }

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            for job in jobs:

                # -------------------------------------------------
                # 没有岗位 ID，跳过
                # -------------------------------------------------

                if not job.source_job_id:

                    stats["skipped"] += 1

                    continue

                # -------------------------------------------------
                # 查询数据库中是否存在
                # -------------------------------------------------

                cursor.execute(
                    """
                    SELECT content_hash
                    FROM jobs
                    WHERE source = %s
                      AND source_job_id = %s
                    """,
                    (
                        job.source,
                        job.source_job_id,
                    ),
                )

                existing = cursor.fetchone()

                # -------------------------------------------------
                # 情况 1：新岗位
                # -------------------------------------------------

                if existing is None:

                    insert_job(
                        cursor,
                        job,
                    )

                    stats["inserted"] += 1

                # -------------------------------------------------
                # 情况 2：岗位内容发生变化
                # -------------------------------------------------

                elif (
                    existing["content_hash"]
                    != job.content_hash
                ):

                    update_job(
                        cursor,
                        job,
                    )

                    stats["updated"] += 1

                # -------------------------------------------------
                # 情况 3：没有变化
                # -------------------------------------------------

                else:

                    stats["unchanged"] += 1

        # 所有数据成功后提交
        connection.commit()

        return stats

    except Exception:

        if connection:
            connection.rollback()

        raise

    finally:

        if connection:
            connection.close()


# =========================================================
# 从 JSON 同步到 MySQL
# =========================================================

def sync_jobs_from_json(
    json_path: str | Path,
) -> dict[str, int]:
    """
    从 JSON 读取岗位，
    然后同步到 MySQL。
    """

    jobs = load_jobs_from_json(
        json_path
    )

    return sync_jobs(
        jobs
    )


# =========================================================
# 直接运行本文件
# =========================================================

if __name__ == "__main__":

    json_file = (
        BASE_DIR
        / "data"
        / "tencent_jobs.json"
    )

    print("=" * 60)
    print("开始同步腾讯岗位到 MySQL")
    print("=" * 60)

    stats = sync_jobs_from_json(
        json_file
    )

    print()
    print("=" * 60)
    print("MySQL 同步完成")
    print("=" * 60)

    print(
        f"新增："
        f"{stats['inserted']}"
    )

    print(
        f"更新："
        f"{stats['updated']}"
    )

    print(
        f"未变化："
        f"{stats['unchanged']}"
    )

    print(
        f"跳过："
        f"{stats['skipped']}"
    )