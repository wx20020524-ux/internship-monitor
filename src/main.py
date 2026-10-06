from src.collectors.registry import get_collector
from src.db.sync import sync_jobs_from_json


# =========================================================
# 公司采集配置
# =========================================================

COMPANY_CONFIGS = {
    "tencent": {
        "keyword": "",
        "max_pages": 1,
    },

    "bytedance": {
        "keyword": "",
        "max_pages": 5,
        "headless": True,
    },
}


# =========================================================
# 单家公司运行
# =========================================================

def run_company(
    company: str,
    config: dict,
) -> dict:
    """
    单家公司完整流程：

        获取采集器
             ↓
        采集岗位
             ↓
        保存 JSON
             ↓
        同步 MySQL
    """

    print()
    print("=" * 70)

    print(
        f"开始处理公司：{company}"
    )

    print("=" * 70)

    # -----------------------------------------------------
    # 1. 获取采集器
    # -----------------------------------------------------

    collector = get_collector(
        company,
        **config,
    )

    # -----------------------------------------------------
    # 2. 采集
    # -----------------------------------------------------

    jobs = collector.collect()

    print()
    print(
        f"[{company}] "
        f"采集完成："
        f"{len(jobs)} 条"
    )

    # -----------------------------------------------------
    # 3. 保存 JSON
    # -----------------------------------------------------

    output_file = collector.save(
        jobs
    )

    print(
        f"[{company}] "
        f"JSON："
        f"{output_file}"
    )

    # -----------------------------------------------------
    # 4. 同步 MySQL
    # -----------------------------------------------------

    stats = sync_jobs_from_json(
        output_file
    )

    print()
    print(
        f"[{company}] "
        "MySQL 同步结果"
    )

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

    return {
        "company": company,
        "jobs": len(jobs),
        "output_file": output_file,
        "stats": stats,
    }


# =========================================================
# 主程序
# =========================================================

def main():

    print("=" * 70)
    print(
        "AI 实时实习信息平台"
    )
    print("=" * 70)

    results = []

    # -----------------------------------------------------
    # 依次处理所有公司
    # -----------------------------------------------------

    for company, config in (
        COMPANY_CONFIGS.items()
    ):

        try:

            result = run_company(
                company,
                config,
            )

            results.append(
                result
            )

        except Exception as error:

            print()
            print("=" * 70)

            print(
                f"[{company}] "
                "处理失败"
            )

            print(
                f"错误：{error}"
            )

            print("=" * 70)

            # 单家公司失败，
            # 不影响其他公司
            continue

    # =====================================================
    # 汇总
    # =====================================================

    print()
    print("=" * 70)

    print(
        "全部公司处理完成"
    )

    print("=" * 70)

    total_jobs = 0
    total_inserted = 0
    total_updated = 0
    total_unchanged = 0
    total_skipped = 0

    for result in results:

        stats = result["stats"]

        total_jobs += (
            result["jobs"]
        )

        total_inserted += (
            stats["inserted"]
        )

        total_updated += (
            stats["updated"]
        )

        total_unchanged += (
            stats["unchanged"]
        )

        total_skipped += (
            stats["skipped"]
        )

        print(
            f"{result['company']}: "
            f"{result['jobs']} 条"
        )

    print()
    print(
        f"总采集岗位："
        f"{total_jobs}"
    )

    print(
        f"总新增："
        f"{total_inserted}"
    )

    print(
        f"总更新："
        f"{total_updated}"
    )

    print(
        f"总未变化："
        f"{total_unchanged}"
    )

    print(
        f"总跳过："
        f"{total_skipped}"
    )


if __name__ == "__main__":
    main()