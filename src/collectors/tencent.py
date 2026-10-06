import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

from src.collectors.base import BaseCollector
from src.models import Job


# =========================================================
# 腾讯招聘 API
# =========================================================

LIST_API_URL = (
    "https://careers.tencent.com/"
    "tencentcareer/api/post/Query"
)

DETAIL_API_URL = (
    "https://careers.tencent.com/"
    "tencentcareer/api/post/ByPostId"
)


class TencentCollector(BaseCollector):
    """
    腾讯招聘岗位采集器。

    功能：
    1. 获取岗位列表
    2. 自动分页
    3. 获取岗位详情
    4. 转换为统一 Job
    5. 生成 content_hash
    6. 岗位去重
    7. 保存 JSON
    """

    COMPANY_NAME = "腾讯"
    SOURCE_NAME = "Tencent"

    # 腾讯招聘接口中用于实习岗位筛选
    INTERNSHIP_ATTR_ID = "3"

    # 每页获取岗位数量
    PAGE_SIZE = 50

    def __init__(
        self,
        keyword: str = "",
        max_pages: int = 3,
    ):
        """
        初始化腾讯招聘采集器。

        keyword:
            搜索关键词，例如：
            AI
            Python
            Agent
            空字符串表示不限制关键词

        max_pages:
            最大采集页数
        """

        # 初始化 BaseCollector
        super().__init__(
            keyword=keyword,
            max_pages=max_pages,
        )

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/153.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": (
                "application/json, "
                "text/plain, */*"
            ),
        }

    # =========================================================
    # 1. 生成岗位内容 Hash
    # =========================================================

    def generate_content_hash(
        self,
        job: Job,
    ) -> str:
        """
        根据岗位核心内容生成 SHA256 Hash。

        用于判断：
        1. 岗位是否发生变化
        2. 岗位是否需要更新
        3. 数据库增量更新
        """

        content = "|".join(
            [
                job.company,
                job.title,
                job.city,
                job.department,
                job.description,
                job.requirements,
            ]
        )

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    # =========================================================
    # 2. 获取岗位列表
    # =========================================================

    def fetch_page(
        self,
        client: httpx.Client,
        page_index: int,
    ) -> dict[str, Any]:
        """
        请求腾讯招聘列表 API。
        """

        params = {
            "timestamp": str(
                int(time.time() * 1000)
            ),

            "countryId": "",
            "cityId": "",
            "bgIds": "",
            "productId": "",
            "categoryId": "",
            "parentCategoryId": "",

            # 实习岗位
            "attrId": self.INTERNSHIP_ATTR_ID,

            # 关键词
            "keyword": self.keyword,

            # 分页
            "pageIndex": page_index,
            "pageSize": self.PAGE_SIZE,

            "language": "zh-cn",
            "area": "cn",
        }

        response = client.get(
            LIST_API_URL,
            params=params,
        )

        print(
            f"[列表] 第 {page_index} 页 "
            f"HTTP {response.status_code}"
        )

        response.raise_for_status()

        return response.json()

    # =========================================================
    # 3. 获取岗位详情
    # =========================================================

    def fetch_detail(
        self,
        client: httpx.Client,
        post_id: str,
    ) -> dict[str, Any] | None:
        """
        根据岗位 PostId 获取详细岗位信息。
        """

        params = {
            "timestamp": str(
                int(time.time() * 1000)
            ),

            "postId": post_id,

            "language": "zh-cn",
        }

        try:
            response = client.get(
                DETAIL_API_URL,
                params=params,
            )

            print(
                f"[详情] {post_id} "
                f"HTTP {response.status_code}"
            )

            response.raise_for_status()

            return response.json()

        except Exception as error:
            print(
                f"[详情] 获取失败 "
                f"{post_id}: {error}"
            )

            # 单个岗位详情失败，
            # 不影响其他岗位继续采集
            return None

    # =========================================================
    # 4. 解析岗位列表
    # =========================================================

    def parse_page(
        self,
        data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        从列表 API 返回结果中提取 Data.Posts。
        """

        data_section = data.get(
            "Data",
            {}
        )

        posts = data_section.get(
            "Posts",
            []
        )

        if not isinstance(
            posts,
            list,
        ):
            return []

        return posts

    # =========================================================
    # 5. 解析岗位详情
    # =========================================================

    def parse_detail(
        self,
        data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        从详情 API 中提取 Data。
        """

        if not data:
            return {}

        data_section = data.get(
            "Data",
            {}
        )

        if not isinstance(
            data_section,
            dict,
        ):
            return {}

        return data_section

    # =========================================================
    # 6. 标准化岗位
    # =========================================================

    def normalize_job(
        self,
        raw_job: dict[str, Any],
        detail: dict[str, Any] | None = None,
    ) -> Job:
        """
        将腾讯原始岗位数据转换成统一 Job 模型。
        """

        detail = detail or {}

        # -----------------------------------------------------
        # 岗位 ID
        # -----------------------------------------------------

        post_id = str(
            raw_job.get(
                "PostId",
                "",
            )
        )

        # -----------------------------------------------------
        # 岗位详情 URL
        # -----------------------------------------------------

        source_url = raw_job.get(
            "PostURL",
            "",
        )

        if not source_url and post_id:
            source_url = (
                "https://careers.tencent.com/"
                "jobdesc.html"
                f"?postId={post_id}"
            )

        # -----------------------------------------------------
        # 工作职责
        # -----------------------------------------------------

        description = (
            detail.get(
                "Responsibility",
                "",
            )
            or raw_job.get(
                "Responsibility",
                "",
            )
        )

        # -----------------------------------------------------
        # 任职要求
        # -----------------------------------------------------

        requirements = (
            detail.get(
                "Requirement",
                "",
            )
            or raw_job.get(
                "Requirement",
                "",
            )
        )

        # -----------------------------------------------------
        # 创建统一 Job
        # -----------------------------------------------------

        job = Job(
            company=self.COMPANY_NAME,

            source=self.SOURCE_NAME,

            source_job_id=post_id,

            title=raw_job.get(
                "RecruitPostName",
                "",
            ),

            city=raw_job.get(
                "LocationName",
                "",
            ),

            country=raw_job.get(
                "CountryName",
                "",
            ),

            department=raw_job.get(
                "BGName",
                "",
            ),

            category=raw_job.get(
                "CategoryName",
                "",
            ),

            experience=raw_job.get(
                "RequireWorkYearsName",
                "",
            ),

            description=description,

            requirements=requirements,

            update_time=raw_job.get(
                "LastUpdateTime",
                "",
            ),

            job_type="实习",

            source_url=source_url,
        )

        # -----------------------------------------------------
        # 创建完整 Job 后生成 content_hash
        # -----------------------------------------------------

        job.content_hash = (
            self.generate_content_hash(job)
        )

        return job

    # =========================================================
    # 7. 岗位去重
    # =========================================================

    def deduplicate(
        self,
        jobs: list[Job],
    ) -> list[Job]:
        """
        根据：

            source + source_job_id

        对岗位进行去重。
        """

        unique_jobs = {}

        for job in jobs:

            # 没有岗位 ID 的数据无法可靠去重
            if not job.source_job_id:
                continue

            key = (
                job.source,
                job.source_job_id,
            )

            unique_jobs[key] = job

        return list(
            unique_jobs.values()
        )

    # =========================================================
    # 8. 完整采集
    # =========================================================

    def collect(self) -> list[Job]:
        """
        执行完整腾讯招聘岗位采集。
        """

        all_jobs: list[Job] = []

        print()
        print("=" * 60)
        print("开始采集腾讯实习岗位")
        print("=" * 60)

        with httpx.Client(
            headers=self.headers,
            timeout=20.0,
            follow_redirects=True,
        ) as client:

            # -------------------------------------------------
            # 自动分页
            # -------------------------------------------------

            for page_index in range(
                1,
                self.max_pages + 1,
            ):

                data = self.fetch_page(
                    client,
                    page_index,
                )

                posts = self.parse_page(
                    data
                )

                print(
                    f"[列表] 本页岗位数："
                    f"{len(posts)}"
                )

                if not posts:

                    print(
                        "[列表] 没有更多岗位，"
                        "停止分页。"
                    )

                    break

                # -------------------------------------------------
                # 处理当前页岗位
                # -------------------------------------------------

                for index, raw_job in enumerate(
                    posts,
                    start=1,
                ):

                    post_id = str(
                        raw_job.get(
                            "PostId",
                            "",
                        )
                    )

                    title = raw_job.get(
                        "RecruitPostName",
                        "",
                    )

                    print(
                        f"  → "
                        f"{index}/{len(posts)} "
                        f"{title} "
                        f"{post_id}"
                    )

                    detail_data = None

                    # -------------------------------------------------
                    # 获取岗位详情
                    # -------------------------------------------------

                    if post_id:
                        detail_data = (
                            self.fetch_detail(
                                client,
                                post_id,
                            )
                        )

                    # -------------------------------------------------
                    # 解析详情
                    # -------------------------------------------------

                    detail = self.parse_detail(
                        detail_data
                    )

                    # -------------------------------------------------
                    # 标准化 Job
                    # -------------------------------------------------

                    job = self.normalize_job(
                        raw_job,
                        detail,
                    )

                    all_jobs.append(
                        job
                    )

                    # 每个岗位之间稍微等待
                    time.sleep(0.2)

                # -------------------------------------------------
                # 腾讯岗位总量
                # -------------------------------------------------

                total = (
                    data
                    .get("Data", {})
                    .get("Count", 0)
                )

                print(
                    f"[列表] 腾讯岗位总数："
                    f"{total}"
                )

                # -------------------------------------------------
                # 是否已经获取全部岗位
                # -------------------------------------------------

                if (
                    total
                    and len(all_jobs) >= total
                ):
                    print(
                        "[列表] 已获取全部岗位，"
                        "停止分页。"
                    )

                    break

                # 页面之间稍微等待
                time.sleep(0.5)

        # =====================================================
        # 去重
        # =====================================================

        unique_jobs = self.deduplicate(
            all_jobs
        )

        print()
        print("=" * 60)
        print("采集统计")
        print("=" * 60)

        print(
            f"原始岗位数量："
            f"{len(all_jobs)}"
        )

        print(
            f"去重后岗位数量："
            f"{len(unique_jobs)}"
        )

        return unique_jobs

    # =========================================================
    # 9. 保存岗位数据
    # =========================================================

    def save(
        self,
        jobs: list[Job],
    ) -> Path:
        """
        将标准化后的岗位保存为 JSON。
        """

        output_dir = Path(
            "data"
        )

        output_dir.mkdir(
            exist_ok=True
        )

        output_file = (
            output_dir
            / "tencent_jobs.json"
        )

        jobs_data = [
            job.model_dump(
                mode="json"
            )
            for job in jobs
        ]

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                jobs_data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print()
        print(
            f"数据已保存："
            f"{output_file}"
        )

        return output_file