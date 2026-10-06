import json

from dotenv import load_dotenv

from src.ai.resume_parser import parse_resume
from src.ai.resume_llm import ResumeLLM
from src.ai.resume_matcher import ResumeMatcher
from src.ai.job_repository import JobRepository


def main():

    # ==========================================
    # 1. 加载 .env
    # ==========================================

    load_dotenv()

    print("=" * 60)
    print("AI 实习岗位智能匹配系统")
    print("=" * 60)

    # ==========================================
    # 2. 读取简历
    # ==========================================

    resume_path = "data/实习简历1.pdf"

    print("\n[1/4] 正在解析简历...")

    resume_text = parse_resume(
        resume_path
    )

    print("简历读取成功")
    print(
        f"文本长度：{len(resume_text)} 字符"
    )

    # ==========================================
    # 3. Qwen 生成 ResumeProfile
    # ==========================================

    print(
        "\n[2/4] 正在使用 Qwen3.8-Flash "
        "生成简历画像..."
    )

    llm = ResumeLLM()

    profile = llm.parse_resume(
        resume_text
    )

    print("ResumeProfile 生成成功")

    print("\n========== 简历画像 ==========")

    print(
        profile.model_dump_json(
            indent=2,
            ensure_ascii=False
        )
    )

    # ==========================================
    # 4. 从 MySQL 获取岗位
    # ==========================================

    print(
        "\n[3/4] 正在读取 MySQL 岗位..."
    )

    repository = JobRepository()

    jobs = repository.get_jobs(
        limit=1000
    )

    print(
        f"MySQL 中读取到 {len(jobs)} 个岗位"
    )

    if not jobs:

        print(
            "\nMySQL jobs 表目前没有岗位数据。"
        )

        return

    # ==========================================
    # 5. 开始匹配
    # ==========================================

    print(
        "\n[4/4] 正在进行岗位匹配..."
    )

    matcher = ResumeMatcher()

    results = matcher.match_jobs(
        profile=profile,
        jobs=jobs,
        top_k=20
    )

    print(
        "\n========== 匹配完成 =========="
    )

    print(
        f"返回 Top {len(results)} 个岗位"
    )

    # ==========================================
    # 6. 输出结果
    # ==========================================

    for index, result in enumerate(
        results,
        start=1
    ):

        print("\n" + "-" * 60)

        print(
            f"第 {index} 名"
        )

        print(
            f"公司：{result['company']}"
        )

        print(
            f"岗位：{result['title']}"
        )

        print(
            f"匹配分数："
            f"{result['match_score']}"
        )

        print(
            f"匹配技能："
            f"{', '.join(result['matched_skills']) or '无'}"
        )

        print(
            f"匹配岗位方向："
            f"{', '.join(result['matched_roles']) or '无'}"
        )

        print(
            "匹配原因："
        )

        for reason in result["reasons"]:
            print(
                f"  - {reason}"
            )


if __name__ == "__main__":
    main()