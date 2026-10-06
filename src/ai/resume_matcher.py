import re
from typing import Any

from src.ai.resume_schema import ResumeProfile


SKILL_ALIASES = {
    "python": {"python"},
    "fastapi": {"fastapi", "fast api"},
    "langchain": {"langchain"},
    "langgraph": {"langgraph"},
    "rag": {"rag", "检索增强生成", "知识库问答"},
    "agent": {"agent", "智能体", "agent开发", "智能代理"},
    "mcp": {"mcp", "模型上下文协议"},
    "mysql": {"mysql", "sql"},
    "redis": {"redis"},
    "docker": {"docker", "容器化"},
    "nginx": {"nginx"},
    "embedding": {"embedding", "向量检索", "文本向量"},
    "llm": {"llm", "大模型", "大型语言模型"},
    "prompt": {"prompt", "提示词", "提示工程"},
    "machine learning": {"machine learning", "机器学习"},
    "deep learning": {"deep learning", "深度学习"},
    "pytorch": {"pytorch", "torch"},
    "cv": {"computer vision", "cv", "计算机视觉"},
    "nlp": {"nlp", "自然语言处理"},
}

ROLE_FAMILIES = {
    "ai": {"ai", "人工智能", "aigc", "大模型", "llm"},
    "agent": {"agent", "智能体"},
    "rag": {"rag", "知识库", "检索增强"},
    "backend": {"backend", "后端", "服务端", "api", "fastapi"},
    "algorithm": {"算法", "algorithm", "机器学习", "深度学习"},
    "cv": {"cv", "计算机视觉", "视觉算法"},
    "nlp": {"nlp", "自然语言处理"},
    "data": {"数据", "data", "数据分析", "商业分析"},
}


class ResumeMatcher:
    """升级后的规则粗筛器：分技能、岗位方向、经历背景、门槛四部分评分。"""

    def match_job(self, profile: ResumeProfile, job: dict[str, Any]) -> dict[str, Any]:
        title = str(job.get("title", ""))
        description = str(job.get("description", ""))
        requirements = str(job.get("requirements", ""))
        education = str(job.get("education", ""))
        experience = str(job.get("experience", ""))
        job_text = " ".join([title, description, requirements]).lower()

        matched_skills = []
        weighted_hits = 0.0
        total_weight = 0.0
        for skill in profile.skills:
            clean = skill.strip()
            if not clean:
                continue
            weight = self._skill_weight(clean)
            total_weight += weight
            aliases = SKILL_ALIASES.get(clean.lower(), {clean.lower()})
            if any(alias.lower() in job_text for alias in aliases):
                matched_skills.append(clean)
                weighted_hits += weight
        skill_score = (weighted_hits / total_weight * 50) if total_weight else 0.0

        matched_roles = self._match_roles(profile.target_roles, title, job_text)
        role_score = min(25.0, len(matched_roles) * 12.5)

        background = " ".join(profile.projects + profile.experience).lower()
        background_keywords = self._extract_background_keywords(background)
        matched_background = [kw for kw in background_keywords if kw.lower() in job_text]
        background_score = min(15.0, len(matched_background) * 3.0)

        threshold_score = self._threshold_score(profile, education, experience, job_text)
        final_score = round(min(100.0, skill_score + role_score + background_score + threshold_score), 2)

        reasons = []
        if matched_skills:
            reasons.append(f"技能匹配：{', '.join(matched_skills[:8])}")
        if matched_roles:
            reasons.append(f"方向匹配：{', '.join(matched_roles)}")
        if matched_background:
            reasons.append(f"项目/经历相关：{', '.join(matched_background[:5])}")
        if threshold_score >= 8:
            reasons.append("学历/经验门槛基本符合")
        if not reasons:
            reasons.append("当前岗位与简历关键词重合较少")

        return {
            "job": job,
            "rule_score": final_score,
            "match_score": final_score,
            "matched_skills": matched_skills,
            "matched_roles": matched_roles,
            "matched_background": matched_background[:8],
            "reasons": reasons,
        }

    def match_jobs(self, profile: ResumeProfile, jobs: list[dict[str, Any]], top_k: int = 20) -> list[dict[str, Any]]:
        results = [self.match_job(profile, job) for job in jobs]
        results.sort(key=lambda item: item["rule_score"], reverse=True)
        return results[:top_k]

    @staticmethod
    def _skill_weight(skill: str) -> float:
        lower = skill.lower()
        high = {"python", "langchain", "langgraph", "rag", "agent", "llm", "fastapi", "embedding"}
        medium = {"mcp", "redis", "mysql", "docker", "pytorch", "nlp", "cv"}
        if lower in high:
            return 1.5
        if lower in medium:
            return 1.2
        return 1.0

    @staticmethod
    def _match_roles(target_roles: list[str], title: str, job_text: str) -> list[str]:
        title_lower = title.lower()
        matched = []
        for role in target_roles:
            role = role.strip()
            if not role:
                continue
            role_lower = role.lower()
            if role_lower in title_lower:
                matched.append(role)
                continue
            for family in ROLE_FAMILIES.values():
                if any(token in role_lower for token in family):
                    if any(token in job_text for token in family):
                        matched.append(role)
                        break
        return matched

    @staticmethod
    def _threshold_score(
        profile: ResumeProfile,
        education: str,
        experience: str,
        job_text: str,
    ) -> float:
        score = 10.0
        education_text = (education or "").lower()
        if education_text:
            graduate = "硕士" in profile.education or "研究生" in profile.education
            if graduate and any(term in education_text for term in ["本科", "本科及以上", "硕士", "研究生"]):
                score += 0
            elif graduate and "博士" in education_text:
                score -= 1

        requirement = f"{experience} {job_text}".lower()
        if re.search(r"[1-9]\s*年以上|\d+\+?年经验", requirement):
            if "应届" in profile.education or "在校" in profile.education:
                score -= 3
        return max(0.0, min(10.0, score))

    @staticmethod
    def _extract_background_keywords(text: str) -> list[str]:
        candidates = [
            "python", "fastapi", "langchain", "langgraph", "rag", "agent", "mcp",
            "mysql", "redis", "docker", "nginx", "embedding", "大模型", "知识库",
            "智能体", "机器学习", "深度学习", "pytorch", "streamlit", "gradio",
        ]
        return [kw for kw in candidates if re.search(re.escape(kw), text, re.IGNORECASE)]
