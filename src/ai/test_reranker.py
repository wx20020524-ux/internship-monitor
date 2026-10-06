from dotenv import load_dotenv

from src.ai.resume_parser import parse_resume
from src.ai.resume_llm import ResumeLLM
from src.ai.resume_matcher import ResumeMatcher
from src.ai.job_repository import JobRepository
from src.ai.resume_reranker import ResumeReranker


def main():

    load_dotenv()

    print("=" * 70)
    print("AI 实习岗位智能推荐系统")
    print("=" * 70)

    # =====================================================
    # 第一步：解析简历
    # =====================================================

    print("\n[1/5] 正在解析简历...")

    resume_path = "data/实习简历1.pdf"

    resume_text = parse_resume(
        resume_path
    )

    print(
        f"简历解析成功，"
        f"文本长度：{len(resume_text)}"
    )

    # =====================================================
    # 第二步：生成 ResumeProfile
    # =====================================================

    print(
        "\n[2/5] 正在生成 ResumeProfile..."
    )

    resume_llm = ResumeLLM()

    profile = resume_llm.parse_resume(
        resume_text
    )

    print("ResumeProfile 生成成功")

    # =====================================================
    # 第三步：读取 MySQL
    # =====================================================

    print(
        "\n[3/5] 正在读取 MySQL 岗位..."
    )

    repository = JobRepository()

    jobs = repository.get_jobs(
        limit=1000
    )

    print(
        f"MySQL读取到 {len(jobs)} 个岗位"
    )

    if not jobs:
        print("当前没有岗位数据。")
        return

    # =====================================================
    # 第四步：规则粗筛
    # =====================================================

    print(
        "\n[4/5] 正在进行规则粗筛..."
    )

    matcher = ResumeMatcher()

    candidate_jobs = matcher.match_jobs(
        profile=profile,
        jobs=jobs,
        top_k=10
    )

    print(
        f"规则匹配完成，"
        f"进入 Qwen 精排："
        f"{len(candidate_jobs)} 个岗位"
    )

    # =====================================================
    # 第五步：Qwen 二次精排
    # =====================================================

    print(
        "\n[5/5] 正在使用 Qwen3.8-Flash 进行二次精排..."
    )

    reranker = ResumeReranker()

    final_results = reranker.rerank(
        profile=profile,
        jobs=candidate_jobs
    )

    # =====================================================
    # 最终结果
    # =====================================================

    print("\n")
    print("=" * 70)
    print("最终岗位推荐结果")
    print("=" * 70)

    for index, result in enumerate(
        final_results,
        start=1
    ):

        job = result["job"]

        print("\n" + "-" * 70)

        print(
            f"第 {index} 个岗位"
        )

        print(
            f"公司：{job.get('company', '')}"
        )

        print(
            f"岗位：{job.get('title', '')}"
        )

        print(
            f"城市：{job.get('city', '')}"
        )

        print(
            f"匹配分数："
            f"{result['match_score']}"
        )

        print(
            "匹配技能："
            + (
                ", ".join(
                    result["matched_skills"]
                )
                if result["matched_skills"]
                else "无"
            )
        )

        print(
            "缺失技能："
            + (
                ", ".join(
                    result["missing_skills"]
                )
                if result["missing_skills"]
                else "无"
            )
        )

        print(
            "相关经历："
        )

        for experience in result[
            "matched_experience"
        ]:
            print(
                f"  - {experience}"
            )

        print(
            "匹配原因："
            f"{result['reason']}"
        )

        print(
            "建议："
            f"{result['suggestion']}"
        )


if __name__ == "__main__":
    main()