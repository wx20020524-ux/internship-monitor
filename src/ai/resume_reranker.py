import json
import re
from typing import Any

from src.ai.llm import chat_with_llm
from src.ai.resume_schema import ResumeProfile


class ResumeReranker:
    """使用 Qwen 对粗筛结果进行二次精排，并保留规则分数。"""

    BATCH_SIZE = 5
    MAX_TEXT_LENGTH = 1800

    def rerank(self, profile: ResumeProfile, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        all_results = []
        for start in range(0, len(jobs), self.BATCH_SIZE):
            batch = jobs[start:start + self.BATCH_SIZE]
            all_results.extend(self._rerank_batch(profile, batch))

        all_results.sort(key=lambda item: item["llm_score"], reverse=True)
        return all_results

    def _rerank_batch(self, profile: ResumeProfile, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        jobs_text = []
        for index, item in enumerate(jobs):
            job = item["job"]
            jobs_text.append(
                f"""
岗位编号：{index}
数据库ID：{job.get('id', '')}
公司：{job.get('company', '')}
岗位名称：{job.get('title', '')}
城市：{job.get('city', '')}
部门：{job.get('department', '')}
类别：{job.get('category', '')}
岗位类型：{job.get('job_type', '')}
学历要求：{job.get('education', '')}
经验要求：{job.get('experience', '')}
岗位描述：{self._truncate(str(job.get('description', '')))}
岗位要求：{self._truncate(str(job.get('requirements', '')))}
规则粗筛分：{item.get('rule_score', 0)}
"""
            )

        prompt = f"""
你是一名严格的技术招聘评估助手。
请根据候选人的真实简历画像，对多个岗位分别进行二次精排。

候选人：
教育背景：{profile.education}
技能：{json.dumps(profile.skills[:30], ensure_ascii=False)}
项目：{json.dumps(profile.projects[:10], ensure_ascii=False)}
经历：{json.dumps(profile.experience[:10], ensure_ascii=False)}
目标岗位：{json.dumps(profile.target_roles[:10], ensure_ascii=False)}

岗位：
{''.join(jobs_text)}

评分标准：
- 技术技能匹配 40%
- 岗位方向与职责匹配 25%
- 项目/实习经历匹配 20%
- 学历/经验门槛 10%
- 成长潜力与岗位场景契合度 5%

要求：
1. 只能使用候选人简历中明确出现的信息。
2. 语义相近的技能可以认为匹配，例如“向量检索”与“Embedding”。
3. 对岗位明确要求但候选人没有体现的技能，填写到 missing_skills。
4. score 为 0-100 的整数。
5. 只返回合法 JSON 数组，不要 Markdown，不要解释。

输出格式：
[
  {{
    "job_index": 0,
    "match_score": 0,
    "matched_skills": [],
    "missing_skills": [],
    "matched_experience": [],
    "reason": "",
    "suggestion": ""
  }}
]
"""

        content = self._clean_json(chat_with_llm(prompt, temperature=0.1))
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("Qwen 精排返回结果不是数组")

        results = []
        for item in data:
            job_index = int(item.get("job_index", -1))
            if not 0 <= job_index < len(jobs):
                continue
            original = jobs[job_index]
            results.append(
                {
                    **original,
                    "llm_score": max(0, min(100, int(item.get("match_score", original.get("rule_score", 0))))),
                    "matched_skills": self._as_list(item.get("matched_skills")),
                    "missing_skills": self._as_list(item.get("missing_skills")),
                    "matched_experience": self._as_list(item.get("matched_experience")),
                    "reason": str(item.get("reason", "")),
                    "suggestion": str(item.get("suggestion", "")),
                }
            )
        return results

    @staticmethod
    def _as_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return []

    @staticmethod
    def _truncate(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
        text = text.strip()
        return text if len(text) <= max_length else text[:max_length] + "..."

    @staticmethod
    def _clean_json(content: str) -> str:
        content = content.strip()
        content = re.sub(r"^```json\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"^```\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        return content.strip()
