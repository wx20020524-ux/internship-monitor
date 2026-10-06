import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from src.collectors.base import BaseCollector
from src.models import Job


# =========================================================
# ByteDance 招聘接口
# =========================================================

SEARCH_API_URL = (
    "https://jobs.bytedance.com/"
    "api/v1/search/job/posts"
)

CAMPUS_POSITION_URL = (
    "https://jobs.bytedance.com/"
    "campus/position"
)


class ByteDanceCollector(BaseCollector):
    """
    字节跳动实习岗位采集器。

    数据流程：

        ByteDance API
             ↓
        原始岗位数据
             ↓
        Job 统一模型
             ↓
        SHA256 content_hash
             ↓
        程序内去重
             ↓
        bytedance_jobs.json
    """

    COMPANY_NAME = "字节跳动"
    SOURCE_NAME = "ByteDance"

    # 当前公开接口中：
    # 202 = 实习
    RECRUITMENT_ID = "202"

    PAGE_SIZE = 50

    OUTPUT_FILE = (
        "data/bytedance_jobs.json"
    )

    # =====================================================
    # 初始化
    # =====================================================

    def __init__(
        self,
        keyword: str = "",
        max_pages: int = 1,
    ):
        super().__init__(
            keyword=keyword,
            max_pages=max_pages,
        )

        # 当前公开实现使用的核心请求头
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/124.0.0.0 "
                "Safari/537.36"
            ),

            "Accept": (
                "application/json, "
                "text/plain, */*"
            ),

            "Content-Type": (
                "application/json"
            ),

            "portal-channel": (
                "campus"
            ),

            "portal-platform": (
                "pc"
            ),

            "website-path": (
                "campus"
            ),

            "Origin": (
                "https://jobs.bytedance.com"
            ),

            "Referer": (
                "https://jobs.bytedance.com/"
                "campus/position"
            ),
        }

    # =====================================================
    # 1. 生成 SHA256
    # =====================================================

    def generate_content_hash(
        self,
        job: Job,
    ) -> str:
        """
        根据岗位核心内容生成 SHA256。
        """

        content = "|".join(
            [
                job.company or "",
                job.title or "",
                job.city or "",
                job.department or "",
                job.description or "",
                job.requirements or "",
            ]
        )

        return hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

    # =====================================================
    # 2. 请求岗位列表
    # =====================================================

    def fetch_page(
        self,
        client: httpx.Client,
        page_index: int,
    ) -> dict[str, Any]:
        """
        获取一页字节实习岗位。
        """

        offset = (
            page_index - 1
        ) * self.PAGE_SIZE

        print()
        print(
            f"[字节列表] 第 "
            f"{page_index} 页"
        )

        print(
            f"          offset={offset}"
        )

        # -------------------------------------------------
        # 当前公开接口的请求体
        # -------------------------------------------------

        payload = {
            "keyword": (
                self.keyword or ""
            ).strip(),

            "limit": self.PAGE_SIZE,

            "offset": offset,

            "portal_type": 3,

            "portal_entrance": 1,

            "language": "zh",

            # 实习
            "recruitment_id_list": [
                self.RECRUITMENT_ID
            ],

            # 当前先不做这些筛选
            "job_category_id_list": [],

            "location_code_list": [],

            "subject_id_list": [],

            "tag_id_list": [],

            "storefront_id_list": [],

            "job_function_id_list": [],
        }

        print(
            "          正在请求 ByteDance API..."
        )

        try:

            response = client.post(
                SEARCH_API_URL,
                headers=self.headers,
                json=payload,
            )

        except httpx.RequestError as error:

            print()
            print(
                "---------- "
                "字节接口网络错误 "
                "----------"
            )

            print(
                error
            )

            print(
                "--------------------------------"
            )

            raise

        print(
            f"          HTTP "
            f"{response.status_code}"
        )

        # -------------------------------------------------
        # 非 2xx：打印完整诊断信息
        # -------------------------------------------------

        if not (
            200
            <= response.status_code
            < 300
        ):

            print()
            print(
                "---------- "
                "字节接口错误响应 "
                "----------"
            )

            print(
                "Request URL:"
            )

            print(
                response.request.url
            )

            print()
            print(
                "Response Headers:"
            )

            for key, value in (
                response.headers.items()
            ):

                # 避免打印不必要的大量响应头
                if key.lower() in {
                    "server",
                    "content-type",
                    "content-length",
                    "allow",
                    "location",
                    "x-request-id",
                }:

                    print(
                        f"{key}: {value}"
                    )

            print()
            print(
                "Response Body:"
            )

            print(
                response.text[:5000]
            )

            print(
                "--------------------------------"
            )

        response.raise_for_status()

        # -------------------------------------------------
        # 解析 JSON
        # -------------------------------------------------

        try:

            data = response.json()

        except ValueError as error:

            print(
                "[字节列表] JSON 解析失败：",
                error,
            )

            print(
                "服务器返回："
            )

            print(
                response.text[:5000]
            )

            raise

        # -------------------------------------------------
        # 检查业务状态
        # -------------------------------------------------

        code = data.get(
            "code"
        )

        if code not in (
            0,
            None,
        ):

            message = data.get(
                "message",
                "unknown error",
            )

            raise RuntimeError(
                "ByteDance API "
                f"业务错误："
                f"code={code}, "
                f"message={message}"
            )

        return data

    # =====================================================
    # 3. 提取岗位列表
    # =====================================================

    def parse_page(
        self,
        data: dict[str, Any],
    ) -> tuple[
        list[dict[str, Any]],
        int,
    ]:
        """
        从 API 返回结果中提取：

        data.job_post_list
        data.count
        """

        data_section = (
            data.get(
                "data"
            )
            or {}
        )

        if not isinstance(
            data_section,
            dict,
        ):
            return [], 0

        posts = (
            data_section.get(
                "job_post_list"
            )
            or []
        )

        total = data_section.get(
            "count",
            0,
        )

        if not isinstance(
            posts,
            list,
        ):
            posts = []

        if not isinstance(
            total,
            int,
        ):
            total = len(posts)

        return (
            posts,
            total,
        )

    # =====================================================
    # 4. 城市提取
    # =====================================================

    def extract_city(
        self,
        raw_job: dict[str, Any],
    ) -> str:
        """
        优先使用 city_list。
        """

        city_list = (
            raw_job.get(
                "city_list"
            )
            or []
        )

        if isinstance(
            city_list,
            list,
        ):

            cities = []

            for city in city_list:

                if not isinstance(
                    city,
                    dict,
                ):
                    continue

                name = city.get(
                    "name",
                    "",
                )

                if name:

                    cities.append(
                        str(name)
                    )

            if cities:

                # 保持原始顺序并去重
                cities = list(
                    dict.fromkeys(
                        cities
                    )
                )

                return " / ".join(
                    cities
                )

        # -------------------------------------------------
        # city_list 没有时，尝试 city_info
        # -------------------------------------------------

        city_info = raw_job.get(
            "city_info"
        )

        if isinstance(
            city_info,
            dict,
        ):

            return str(
                city_info.get(
                    "name",
                    "",
                )
            )

        return ""

    # =====================================================
    # 5. 岗位类别
    # =====================================================

    def extract_category(
        self,
        raw_job: dict[str, Any],
    ) -> str:

        category = raw_job.get(
            "job_category"
        )

        if isinstance(
            category,
            dict,
        ):

            return str(
                category.get(
                    "name",
                    "",
                )
            )

        if isinstance(
            category,
            str,
        ):

            return category

        return ""

    # =====================================================
    # 6. 招聘类型
    # =====================================================

    def extract_job_type(
        self,
        raw_job: dict[str, Any],
    ) -> str:

        recruit_type = raw_job.get(
            "recruit_type"
        )

        if isinstance(
            recruit_type,
            dict,
        ):

            name = recruit_type.get(
                "name",
                "",
            )

            if name:

                return str(name)

        if isinstance(
            recruit_type,
            str,
        ):

            return recruit_type

        return "实习"

    # =====================================================
    # 7. 时间转换
    # =====================================================

    def format_time(
        self,
        value: Any,
    ) -> str:
        """
        ByteDance 接口时间通常是 Unix 时间戳。
        同时兼容已经是字符串的情况。
        """

        if value in (
            None,
            "",
        ):
            return ""

        # 已经是字符串
        if isinstance(
            value,
            str,
        ):

            return value

        try:

            timestamp = int(
                value
            )

            # 毫秒级时间戳
            if timestamp > 10_000_000_000:

                timestamp = (
                    timestamp / 1000
                )

            return datetime.fromtimestamp(
                timestamp
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        except (
            ValueError,
            TypeError,
            OSError,
        ):

            return str(value)

    # =====================================================
    # 8. 标准化 Job
    # =====================================================

    def normalize_job(
        self,
        raw_job: dict[str, Any],
    ) -> Job:
        """
        ByteDance 原始岗位 → 统一 Job。
        """

        # -------------------------------------------------
        # 岗位 ID
        # -------------------------------------------------

        post_id = str(
            raw_job.get(
                "id",
                "",
            )
        )

        # -------------------------------------------------
        # 标题
        # -------------------------------------------------

        title = str(
            raw_job.get(
                "title",
                "",
            )
            or ""
        )

        # -------------------------------------------------
        # 城市
        # -------------------------------------------------

        city = self.extract_city(
            raw_job
        )

        # -------------------------------------------------
        # 岗位类别
        # -------------------------------------------------

        category = (
            self.extract_category(
                raw_job
            )
        )

        # -------------------------------------------------
        # 招聘类型
        # -------------------------------------------------

        job_type = (
            self.extract_job_type(
                raw_job
            )
        )

        # -------------------------------------------------
        # JD
        # -------------------------------------------------

        description = str(
            raw_job.get(
                "description",
                "",
            )
            or ""
        )

        # -------------------------------------------------
        # 任职要求
        # -------------------------------------------------

        requirements = str(
            raw_job.get(
                "requirement",
                "",
            )
            or ""
        )

        # -------------------------------------------------
        # 时间
        # -------------------------------------------------

        publish_time = (
            self.format_time(
                raw_job.get(
                    "publish_time"
                )
            )
        )

        update_time = (
            self.format_time(
                raw_job.get(
                    "update_time"
                )
            )
        )

        # 如果接口没有单独的 update_time，
        # 则使用 publish_time
        if not update_time:

            update_time = publish_time

        # -------------------------------------------------
        # 岗位 URL
        # -------------------------------------------------

        if post_id:

            source_url = (
                f"{CAMPUS_POSITION_URL}/"
                f"{post_id}/detail"
            )

        else:

            source_url = (
                CAMPUS_POSITION_URL
            )

        # -------------------------------------------------
        # 构造统一 Job
        # -------------------------------------------------

        job = Job(
            company=self.COMPANY_NAME,

            source=self.SOURCE_NAME,

            source_job_id=post_id,

            title=title,

            city=city,

            country="",

            department="",

            category=category,

            salary="",

            education="",

            experience="",

            description=description,

            requirements=requirements,

            job_type=job_type,

            publish_time=publish_time,

            update_time=update_time,

            source_url=source_url,
        )

        # -------------------------------------------------
        # content_hash
        # -------------------------------------------------

        job.content_hash = (
            self.generate_content_hash(
                job
            )
        )

        return job

    # =====================================================
    # 9. 岗位去重
    # =====================================================

    def deduplicate(
        self,
        jobs: list[Job],
    ) -> list[Job]:
        """
        使用：

            source + source_job_id

        作为岗位唯一键。
        """

        unique_jobs: dict[
            tuple[str, str],
            Job,
        ] = {}

        for job in jobs:

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

    # =====================================================
    # 10. 完整采集
    # =====================================================

    def collect(
        self,
    ) -> list[Job]:

        all_jobs: list[Job] = []

        print()
        print("=" * 60)
        print(
            "开始采集字节跳动实习岗位"
        )
        print("=" * 60)

        # -------------------------------------------------
        # 非常重要：
        #
        # trust_env=False
        #
        # 不读取：
        # HTTP_PROXY
        # HTTPS_PROXY
        # ALL_PROXY
        # -------------------------------------------------

        with httpx.Client(
            headers=self.headers,
            timeout=30.0,
            trust_env=False,
            follow_redirects=True,
        ) as client:

            total = None

            for page_index in range(
                1,
                self.max_pages + 1,
            ):

                data = self.fetch_page(
                    client,
                    page_index,
                )

                posts, page_total = (
                    self.parse_page(
                        data
                    )
                )

                if total is None:

                    total = page_total

                print(
                    f"          "
                    f"本页岗位数："
                    f"{len(posts)}"
                )

                print(
                    f"          "
                    f"接口总数："
                    f"{page_total}"
                )

                # -------------------------------------------------
                # 没有岗位
                # -------------------------------------------------

                if not posts:

                    print(
                        "          "
                        "没有更多岗位，"
                        "停止分页。"
                    )

                    break

                # -------------------------------------------------
                # 转换 Job
                # -------------------------------------------------

                for index, raw_job in enumerate(
                    posts,
                    start=1,
                ):

                    try:

                        job = (
                            self.normalize_job(
                                raw_job
                            )
                        )

                        all_jobs.append(
                            job
                        )

                        print(
                            f"  → "
                            f"{index}/"
                            f"{len(posts)} "
                            f"{job.title}"
                        )

                    except Exception as error:

                        print(
                            f"  → "
                            f"{index}/"
                            f"{len(posts)} "
                            f"岗位解析失败："
                            f"{error}"
                        )

                # -------------------------------------------------
                # 本页不足 PAGE_SIZE
                # -------------------------------------------------

                if (
                    len(posts)
                    < self.PAGE_SIZE
                ):

                    print(
                        "          "
                        "本页不足 PAGE_SIZE，"
                        "停止分页。"
                    )

                    break

                # -------------------------------------------------
                # 达到总量
                # -------------------------------------------------

                if (
                    total is not None
                    and total > 0
                    and len(all_jobs) >= total
                ):

                    print(
                        "          "
                        "已经获取全部岗位，"
                        "停止分页。"
                    )

                    break

        # =====================================================
        # 去重
        # =====================================================

        unique_jobs = (
            self.deduplicate(
                all_jobs
            )
        )

        print()
        print("=" * 60)
        print(
            "字节跳动采集统计"
        )
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

    # =====================================================
    # 11. 保存 JSON
    # =====================================================

    def save(
        self,
        jobs: list[Job],
    ) -> Path:
        """
        保存：

            data/bytedance_jobs.json
        """

        output_file = Path(
            self.OUTPUT_FILE
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
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
            "字节岗位数据已保存："
            f"{output_file}"
        )

        return output_file


# =========================================================
# 单独测试
# =========================================================

if __name__ == "__main__":

    collector = ByteDanceCollector(
        keyword="",
        max_pages=1,
    )

    jobs = collector.collect()

    output_file = collector.save(
        jobs
    )

    print()
    print("=" * 60)
    print(
        "字节跳动单独测试完成"
    )
    print("=" * 60)

    print(
        f"岗位数量："
        f"{len(jobs)}"
    )

    print(
        f"JSON："
        f"{output_file}"
    )

    print()

    for index, job in enumerate(
        jobs[:5],
        start=1,
    ):

        print(
            f"【岗位 {index}】"
        )

        print(
            f"职位："
            f"{job.title}"
        )

        print(
            f"城市："
            f"{job.city}"
        )

        print(
            f"类别："
            f"{job.category}"
        )

        print(
            f"招聘类型："
            f"{job.job_type}"
        )

        print(
            f"JD 长度："
            f"{len(job.description)}"
        )

        print(
            f"任职要求长度："
            f"{len(job.requirements)}"
        )

        print(
            f"发布时间："
            f"{job.publish_time}"
        )

        print(
            f"更新时间："
            f"{job.update_time}"
        )

        print(
            f"链接："
            f"{job.source_url}"
        )

        print(
            "-" * 60
        )