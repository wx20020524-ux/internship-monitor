import json
import re

from src.ai.llm import chat_with_llm
from src.ai.resume_schema import ResumeProfile


class ResumeLLM:

    def parse_resume(self, resume_text: str) -> ResumeProfile:

        prompt = f"""
你是一名专业的简历信息结构化分析助手。

请分析下面的简历文本，并提取以下信息。

【1. education】

提取候选人的教育背景。
使用简洁的一段文字描述。

【2. skills】

提取候选人的技能。
返回字符串列表。

【3. projects】

提取候选人的项目经历。
每个项目用一句简洁的话描述。

【4. experience】

提取候选人的实习、工作或实践经历。
每段经历用一句简洁的话描述。

【5. target_roles】

根据候选人的教育背景、技能、项目和经历，
分析候选人适合关注的岗位方向。

例如：

[
    "AI应用开发",
    "大模型应用开发",
    "Agent开发"
]

注意：

1. 必须返回合法 JSON。
2. 不要返回 Markdown。
3. 不要返回 ```json。
4. 不要添加任何解释。
5. 不要虚构简历中不存在的事实。
6. 如果没有相关信息，返回空字符串或空数组。

必须严格按照下面格式返回：

{{
    "education": "",
    "skills": [],
    "projects": [],
    "experience": [],
    "target_roles": []
}}

下面是简历原文：

{resume_text}
"""

        # 调用项目中已经验证成功的 LLM
        content = chat_with_llm(prompt)

        print("\n========== Qwen 原始返回 ==========")
        print(content)
        print("====================================\n")

        # 清理可能存在的 Markdown
        content = self._clean_json(content)

        # JSON 字符串 → Python 字典
        data = json.loads(content)

        # Python 字典 → ResumeProfile
        return ResumeProfile(**data)

    @staticmethod
    def _clean_json(content: str) -> str:

        content = content.strip()

        # 去掉 ```json
        content = re.sub(
            r"^```json\s*",
            "",
            content,
            flags=re.IGNORECASE
        )

        # 去掉 ```
        content = re.sub(
            r"^```\s*",
            "",
            content
        )

        content = re.sub(
            r"\s*```$",
            "",
            content
        )

        return content.strip()