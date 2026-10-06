import hashlib
from pathlib import Path
from typing import Any

from src.ai.embedding import EmbeddingMatcher
from src.ai.job_repository import JobRepository
from src.ai.resume_llm import ResumeLLM
from src.ai.resume_matcher import ResumeMatcher
from src.ai.resume_parser import parse_resume
from src.ai.resume_reranker import ResumeReranker
from src.cache.redis import cache


class ResumeMatchService:
    """两阶段匹配：规则 + 可选 Embedding 召回 + Qwen 精排。"""

    JOB_POOL_LIMIT = 2000
    RULE_TOP_K = 20
    SEMANTIC_TOP_K = 20
    FINAL_TOP_K = 10

    def __init__(self):
        self.resume_llm = ResumeLLM()
        self.job_repository = JobRepository()
        self.matcher = ResumeMatcher()
        self.reranker = ResumeReranker()
        self.embedding_matcher = EmbeddingMatcher()

    def match_resume(self, resume_path: str) -> dict[str, Any]:
        resume_text = parse_resume(resume_path)
        if not resume_text.strip():
            raise ValueError("没有从简历中提取到有效文本")

        profile = self.resume_llm.parse_resume(resume_text)
        jobs = self.job_repository.get_jobs(limit=self.JOB_POOL_LIMIT)
        if not jobs:
            raise ValueError("MySQL jobs 表中没有岗位数据")

        rule_candidates = self.matcher.match_jobs(
            profile=profile,
            jobs=jobs,
            top_k=self.RULE_TOP_K,
        )

        semantic_candidates = []
        semantic_enabled = False
        try:
            semantic_candidates, semantic_enabled = self.embedding_matcher.semantic_rank(
                profile,
                jobs,
                top_k=self.SEMANTIC_TOP_K,
            )
        except Exception as error:
            print(f"Embedding 召回暂不可用，回退规则匹配：{error}")

        # 合并去重：规则召回 + 语义召回
        candidate_map: dict[int, dict[str, Any]] = {}
        for item in rule_candidates:
            job_id = item["job"].get("id")
            if job_id is not None:
                candidate_map[int(job_id)] = item
        for item in semantic_candidates:
            job = item["job"]
            job_id = job.get("id")
            if job_id is None:
                continue
            merged = self.matcher.match_job(profile, job)
            merged["semantic_score"] = item["semantic_score"]
            merged["rule_score"] = merged.get("rule_score", 0)
            candidate_map[int(job_id)] = merged

        candidate_jobs = list(candidate_map.values())
        candidate_jobs.sort(
            key=lambda item: (item.get("semantic_score", 0) * 0.5 + item.get("rule_score", 0) * 0.5),
            reverse=True,
        )
        candidate_jobs = candidate_jobs[: max(self.RULE_TOP_K, self.SEMANTIC_TOP_K)]

        try:
            final_results = self.reranker.rerank(profile, candidate_jobs)
        except Exception as error:
            print(f"Qwen 精排失败，回退粗筛结果：{error}")
            final_results = [
                {
                    **item,
                    "llm_score": item.get("rule_score", 0),
                    "reason": "规则匹配结果（LLM 精排暂不可用）",
                    "suggestion": "补充岗位要求中的核心技能后可进一步提升匹配度。",
                    "matched_experience": [],
                    "missing_skills": [],
                }
                for item in candidate_jobs
            ]

        recommendations = []
        for result in final_results[: self.FINAL_TOP_K]:
            job = result["job"]
            rule_score = float(result.get("rule_score", 0))
            llm_score = float(result.get("llm_score", rule_score))
            semantic_score = float(result.get("semantic_score", 0))
            final_score = round(rule_score * 0.35 + llm_score * 0.65, 1)
            recommendations.append(
                {
                    "id": job.get("id"),
                    "company": job.get("company", ""),
                    "title": job.get("title", ""),
                    "city": job.get("city", ""),
                    "department": job.get("department", ""),
                    "category": job.get("category", ""),
                    "job_type": job.get("job_type", ""),
                    "education": job.get("education", ""),
                    "experience": job.get("experience", ""),
                    "salary": job.get("salary", ""),
                    "publish_time": job.get("publish_time", ""),
                    "update_time": job.get("update_time", ""),
                    "source": job.get("source", ""),
                    "source_url": job.get("source_url", ""),
                    "match_score": final_score,
                    "rule_score": round(rule_score, 1),
                    "llm_score": round(llm_score, 1),
                    "semantic_score": round(semantic_score, 1),
                    "matched_skills": result.get("matched_skills", []),
                    "missing_skills": result.get("missing_skills", []),
                    "matched_experience": result.get("matched_experience", []),
                    "reason": result.get("reason", ""),
                    "suggestion": result.get("suggestion", ""),
                }
            )

        return {
            "profile": profile.model_dump(mode="json"),
            "total_jobs": len(jobs),
            "candidate_jobs": len(candidate_jobs),
            "semantic_enabled": semantic_enabled,
            "recommendations": recommendations,
        }

    @staticmethod
    def cache_key_for_file(data: bytes) -> str:
        return f"resume-match:v2:{hashlib.sha256(data).hexdigest()}"

    @staticmethod
    def get_cached_result(key: str) -> dict[str, Any] | None:
        value = cache.get_json(key)
        return value if isinstance(value, dict) else None

    @staticmethod
    def cache_result(key: str, result: dict[str, Any]) -> None:
        cache.set_json(key, result, ttl=1800)
