from dotenv import load_dotenv

from src.ai.resume_parser import parse_resume
from src.ai.resume_llm import ResumeLLM


def main():

    # 加载 .env
    load_dotenv()

    # 简历文件
    resume_path = "data/实习简历1.pdf"

    print("=" * 60)
    print("AI 简历解析系统")
    print("=" * 60)

    # ==============================
    # 第一步：解析简历
    # ==============================

    print("\n[1/3] 正在读取简历...")

    resume_text = parse_resume(resume_path)

    print("简历读取成功")
    print(f"文本长度：{len(resume_text)} 字符")

    # ==============================
    # 第二步：调用 Qwen
    # ==============================

    print("\n[2/3] 正在调用 Qwen3.8-Flash...")

    llm = ResumeLLM()

    profile = llm.parse_resume(resume_text)

    print("Qwen 解析成功")

    # ==============================
    # 第三步：输出 ResumeProfile
    # ==============================

    print("\n[3/3] ResumeProfile")
    print("=" * 60)

    print(
        profile.model_dump_json(
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()