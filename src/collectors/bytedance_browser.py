import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import (
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.collectors.base import BaseCollector
from src.models import Job


# =========================================================
# ByteDance 官方招聘页面
# =========================================================

CAMPUS_POSITION_URL = (
    "https://jobs.bytedance.com/"
    "campus/position?type=3"
)

SEARCH_API_PATH = (
    "/api/v1/search/job/posts"
)


class ByteDanceBrowserCollector(BaseCollector):
    """
    字节跳动浏览器版岗位采集器。

    核心流程：

        打开官方招聘页面
                ↓
        官方 JS 自动生成 _signature
                ↓
        官方页面发起搜索请求
                ↓
        Playwright 捕获真实 API
                ↓
        解析岗位
                ↓
        current=1 / 2 / 3 ...
                ↓
        多页采集
                ↓
        Job
                ↓
        SHA256
                ↓
        去重
                ↓
        bytedance_jobs.json
    """

    COMPANY_NAME = "字节跳动"

    SOURCE_NAME = "ByteDance"

    # =====================================================
    # 最终 JSON
    # =====================================================

    OUTPUT_FILE = (
        "data/bytedance_jobs.json"
    )

    # =====================================================
    # 原始分页 JSON
    # =====================================================

    RAW_DIR = (
        Path("data")
        / "bytedance_raw_pages"
    )

    # =====================================================
    # 根据你实际捕获到的接口：
    #
    # limit=10
    # =====================================================

    PAGE_SIZE = 10

    # =====================================================
    # 初始化
    # =====================================================

    def __init__(
        self,
        keyword: str = "",
        max_pages: int = 5,
        headless: bool = True,
    ):
        super().__init__(
            keyword=keyword,
            max_pages=max_pages,
        )

        self.headless = headless

        # -------------------------------------------------
        # 已经成功处理过的 offset
        # -------------------------------------------------

        self.seen_offsets: set[int] = set()

        # -------------------------------------------------
        # API 返回的岗位总数
        # -------------------------------------------------

        self.total_jobs: int | None = None

        # -------------------------------------------------
        # 所有岗位
        # -------------------------------------------------

        self.all_jobs: list[Job] = []

    # =====================================================
    # 1. 生成 content_hash
    # =====================================================

    def generate_content_hash(
        self,
        job: Job,
    ) -> str:
        """
        根据岗位核心字段生成 SHA256。
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
    # 2. 时间处理
    # =====================================================

    def format_time(
        self,
        value: Any,
    ) -> str:
        """
        兼容：

        1. Unix 秒级时间戳
        2. Unix 毫秒级时间戳
        3. 已经是字符串的时间
        """

        if value in (
            None,
            "",
        ):
            return ""

        # -------------------------------------------------
        # 已经是字符串
        # -------------------------------------------------

        if isinstance(
            value,
            str,
        ):
            return value

        try:

            timestamp = int(value)

            # -------------------------------------------------
            # 毫秒级时间戳
            # -------------------------------------------------

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
    # 3. 从 URL 中提取 offset
    # =====================================================

    def extract_offset(
        self,
        url: str,
    ) -> int | None:
        """
        例如：

        https://jobs.bytedance.com/api/v1/search/job/posts
        ?keyword=&limit=10&offset=20&...

        提取：

            20
        """

        try:

            parsed_url = urlparse(
                url
            )

            query = parse_qs(
                parsed_url.query
            )

            values = query.get(
                "offset"
            )

            if not values:

                return None

            return int(
                values[0]
            )

        except (
            ValueError,
            TypeError,
        ):

            return None

    # =====================================================
    # 4. 提取城市
    # =====================================================

    def extract_city(
        self,
        raw_job: dict[str, Any],
    ) -> str:
        """
        优先解析 city_list。
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

                # 保持顺序去重
                cities = list(
                    dict.fromkeys(
                        cities
                    )
                )

                return " / ".join(
                    cities
                )

        # -------------------------------------------------
        # 兼容 city_info
        # -------------------------------------------------

        city_info = (
            raw_job.get(
                "city_info"
            )
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

        category = (
            raw_job.get(
                "job_category"
            )
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

        recruit_type = (
            raw_job.get(
                "recruit_type"
            )
        )

        if isinstance(
            recruit_type,
            dict,
        ):

            name = (
                recruit_type.get(
                    "name",
                    "",
                )
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
    # 7. 标准化 Job
    # =====================================================

    def normalize_job(
        self,
        raw_job: dict[str, Any],
    ) -> Job:
        """
        将 ByteDance 原始岗位
        转换成统一 Job 模型。
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
        # JD 描述
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
        # 发布时间
        # -------------------------------------------------

        publish_time = (
            self.format_time(
                raw_job.get(
                    "publish_time"
                )
            )
        )

        # -------------------------------------------------
        # 更新时间
        # -------------------------------------------------

        update_time = (
            self.format_time(
                raw_job.get(
                    "update_time"
                )
            )
        )

        # 如果没有 update_time，
        # 用 publish_time 作为兜底
        if not update_time:

            update_time = (
                publish_time
            )

        # -------------------------------------------------
        # 岗位详情 URL
        # -------------------------------------------------

        if post_id:

            source_url = (
                "https://jobs.bytedance.com/"
                "campus/position/"
                f"{post_id}/detail"
            )

        else:

            source_url = (
                "https://jobs.bytedance.com/"
                "campus/position"
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

            # 当前公开搜索接口中
            # 暂时没有稳定 BG 映射
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
    # 8. 解析 API 响应
    # =====================================================

    def parse_response(
        self,
        response: Response,
    ) -> tuple[
        list[Job],
        int,
    ]:
        """
        解析 ByteDance API。

        返回：

            jobs
            total
        """

        # -------------------------------------------------
        # JSON
        # -------------------------------------------------

        try:

            data = response.json()

        except Exception as error:

            print(
                "[字节] JSON 解析失败：",
                error,
            )

            return (
                [],
                0,
            )

        if not isinstance(
            data,
            dict,
        ):

            return (
                [],
                0,
            )

        # -------------------------------------------------
        # 业务状态
        # -------------------------------------------------

        code = data.get(
            "code"
        )

        if code not in (
            0,
            None,
        ):

            print(
                "[字节] API 业务错误：",
                data.get(
                    "message",
                    "",
                ),
            )

            return (
                [],
                0,
            )

        # -------------------------------------------------
        # data
        # -------------------------------------------------

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

            return (
                [],
                0,
            )

        # -------------------------------------------------
        # 岗位列表
        # -------------------------------------------------

        posts = (
            data_section.get(
                "job_post_list"
            )
            or []
        )

        # -------------------------------------------------
        # 总岗位数
        # -------------------------------------------------

        total = (
            data_section.get(
                "count",
                0,
            )
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

        jobs: list[Job] = []

        # -------------------------------------------------
        # 转换 Job
        # -------------------------------------------------

        for raw_job in posts:

            if not isinstance(
                raw_job,
                dict,
            ):

                continue

            try:

                job = (
                    self.normalize_job(
                        raw_job
                    )
                )

                jobs.append(
                    job
                )

            except Exception as error:

                print(
                    "[字节] 岗位解析失败：",
                    error,
                )

        return (
            jobs,
            total,
        )

    # =====================================================
    # 9. 保存原始分页数据
    # =====================================================

    def save_raw_page(
        self,
        offset: int,
        response: Response,
    ) -> None:
        """
        每成功采集一页，
        就把原始 API 响应保存下来。

        例如：

            page_0001.json
            page_0002.json
            page_0003.json
        """

        try:

            data = response.json()

        except Exception:

            return

        self.RAW_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        page_number = (
            offset // self.PAGE_SIZE
        ) + 1

        output_file = (
            self.RAW_DIR
            / f"page_{page_number:04d}.json"
        )

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"[字节] 原始第 "
            f"{page_number} 页已保存："
            f"{output_file}"
        )

    # =====================================================
    # 10. 处理真实 API 响应
    # =====================================================

    def process_response(
        self,
        response: Response,
    ) -> bool:
        """
        处理一次真实岗位接口响应。

        只有 HTTP 200 才处理。
        """

        # -------------------------------------------------
        # HTTP
        # -------------------------------------------------

        if response.status != 200:

            return False

        # -------------------------------------------------
        # 确认是岗位搜索接口
        # -------------------------------------------------

        if (
            SEARCH_API_PATH
            not in response.url
        ):

            return False

        # -------------------------------------------------
        # offset
        # -------------------------------------------------

        offset = (
            self.extract_offset(
                response.url
            )
        )

        if offset is None:

            print(
                "[字节] 无法从接口 URL "
                "获取 offset："
            )

            print(
                response.url
            )

            return False

        # -------------------------------------------------
        # 防止重复处理
        # -------------------------------------------------

        if offset in self.seen_offsets:

            return True

        # -------------------------------------------------
        # 解析
        # -------------------------------------------------

        jobs, total = (
            self.parse_response(
                response
            )
        )

        # -------------------------------------------------
        # 更新总数
        # -------------------------------------------------

        self.total_jobs = total

        # -------------------------------------------------
        # 保存原始响应
        # -------------------------------------------------

        self.save_raw_page(
            offset,
            response,
        )

        # -------------------------------------------------
        # 标记 offset
        # -------------------------------------------------

        self.seen_offsets.add(
            offset
        )

        # -------------------------------------------------
        # 累积岗位
        # -------------------------------------------------

        self.all_jobs.extend(
            jobs
        )

        # -------------------------------------------------
        # 当前页码
        # -------------------------------------------------

        page_number = (
            offset // self.PAGE_SIZE
        ) + 1

        # -------------------------------------------------
        # 打印统计
        # -------------------------------------------------

        print()
        print("=" * 60)

        print(
            f"[字节] 第 "
            f"{page_number} 页捕获成功"
        )

        print(
            f"       offset："
            f"{offset}"
        )

        print(
            f"       本页岗位："
            f"{len(jobs)}"
        )

        print(
            f"       接口总岗位："
            f"{total}"
        )

        print(
            f"       当前累计："
            f"{len(self.all_jobs)}"
        )

        print(
            "=" * 60
        )

        # -------------------------------------------------
        # 打印本页岗位
        # -------------------------------------------------

        for index, job in enumerate(
            jobs,
            start=1,
        ):

            print(
                f"  {index:02d}. "
                f"{job.title}"
            )

        return True

    # =====================================================
    # 11. 通过 current 参数加载指定页
    # =====================================================

    def load_page_by_number(
        self,
        page: Page,
        page_number: int,
    ) -> bool:
        """
        访问指定页。

        current=1 → offset=0
        current=2 → offset=10
        current=3 → offset=20
        ...

        每次由官方页面自己生成 _signature。
        """

        # -------------------------------------------------
        # 计算这一页理论上的 offset
        # -------------------------------------------------

        expected_offset = (
            page_number - 1
        ) * self.PAGE_SIZE

        # -------------------------------------------------
        # 官方页面 URL
        # -------------------------------------------------

        page_url = (
            "https://jobs.bytedance.com/"
            "campus/position"
            f"?type=3"
            f"&current={page_number}"
            f"&limit={self.PAGE_SIZE}"
        )

        print()
        print("=" * 60)

        print(
            f"[字节] 准备加载第 "
            f"{page_number} 页"
        )

        print(
            f"       current="
            f"{page_number}"
        )

        print(
            f"       期望 offset="
            f"{expected_offset}"
        )

        print(
            f"       URL="
            f"{page_url}"
        )

        print("=" * 60)

        try:

            # -------------------------------------------------
            # 核心：
            #
            # 只等待当前页对应的 API 响应
            #
            # 不再使用 page.on("response")
            # -------------------------------------------------

            with page.expect_response(
                lambda response:
                    (
                        SEARCH_API_PATH
                        in response.url
                        and response.status == 200
                        and (
                            self.extract_offset(
                                response.url
                            )
                            == expected_offset
                        )
                    ),
                timeout=30_000,
            ) as response_info:

                page.goto(
                    page_url,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

            response = (
                response_info.value
            )

            # -------------------------------------------------
            # 处理唯一的目标响应
            # -------------------------------------------------

            success = (
                self.process_response(
                    response
                )
            )

            if success:

                print()
                print(
                    f"[字节] 第 "
                    f"{page_number} 页加载成功"
                )

            return success

        except PlaywrightTimeoutError:

            print()
            print(
                f"[字节] 第 "
                f"{page_number} 页超时"
            )

            print(
                f"       30 秒内没有捕获："
                f"offset={expected_offset}"
                f" 的 HTTP 200 请求"
            )

            return False

        except Exception as error:

            print()
            print(
                f"[字节] 第 "
                f"{page_number} 页加载失败："
            )

            print(
                error
            )

            return False

    # =====================================================
    # 12. 完整分页采集
    # =====================================================

    def collect(
        self,
    ) -> list[Job]:
        """
        连续采集多个页面。
        """

        # -------------------------------------------------
        # 重置状态
        # -------------------------------------------------

        self.all_jobs = []

        self.seen_offsets = set()

        self.total_jobs = None

        print()
        print("=" * 70)

        print(
            "开始稳定采集 "
            "ByteDance 实习岗位"
        )

        print("=" * 70)

        print(
            f"最大页数："
            f"{self.max_pages}"
        )

        print(
            f"每页岗位："
            f"{self.PAGE_SIZE}"
        )

        # =================================================
        # 启动 Playwright
        # =================================================

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=self.headless,
            )

            context = browser.new_context(

                viewport={
                    "width": 1440,
                    "height": 900,
                },

                locale="zh-CN",

                user_agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/124.0.0.0 "
                    "Safari/537.36"
                ),
            )

            page = context.new_page()

            # =================================================
            # 注意：
            #
            # 这里故意没有：
            #
            # page.on("response", ...)
            #
            # 因为每一页由 load_page_by_number()
            # 使用 expect_response() 精确等待。
            # =================================================

            # =================================================
            # 逐页采集
            # =================================================

            for page_number in range(
                1,
                self.max_pages + 1,
            ):

                expected_offset = (
                    page_number - 1
                ) * self.PAGE_SIZE

                # -------------------------------------------------
                # 已经处理过就跳过
                # -------------------------------------------------

                if (
                    expected_offset
                    in self.seen_offsets
                ):

                    print()
                    print(
                        f"[字节] "
                        f"offset={expected_offset} "
                        "已经捕获，跳过"
                    )

                    continue

                # -------------------------------------------------
                # 加载这一页
                # -------------------------------------------------

                success = (
                    self.load_page_by_number(
                        page,
                        page_number,
                    )
                )

                # -------------------------------------------------
                # 当前页失败
                # -------------------------------------------------

                if not success:

                    print()
                    print(
                        f"[字节] 第 "
                        f"{page_number} 页失败"
                    )

                    print(
                        "       停止分页"
                    )

                    break

                # -------------------------------------------------
                # 检查是否已经达到总岗位数
                # -------------------------------------------------

                if (
                    self.total_jobs
                    is not None
                    and self.total_jobs > 0
                    and len(self.all_jobs)
                    >= self.total_jobs
                ):

                    print()
                    print(
                        "[字节] "
                        "已经达到接口总岗位数"
                    )

                    break

                # -------------------------------------------------
                # 页面之间等待
                # -------------------------------------------------

                page.wait_for_timeout(
                    1_000
                )

            # -------------------------------------------------
            # 关闭浏览器
            # -------------------------------------------------

            browser.close()

        # =====================================================
        # 最终去重
        # =====================================================

        unique_jobs: dict[
            tuple[str, str],
            Job,
        ] = {}

        for job in self.all_jobs:

            if not job.source_job_id:

                continue

            key = (
                job.source,
                job.source_job_id,
            )

            unique_jobs[key] = job

        jobs = list(
            unique_jobs.values()
        )

        # =====================================================
        # 最终统计
        # =====================================================

        print()
        print("=" * 70)

        print(
            "ByteDance 分页采集完成"
        )

        print("=" * 70)

        print(
            f"成功页数："
            f"{len(self.seen_offsets)}"
        )

        print(
            f"成功 offset："
            f"{sorted(self.seen_offsets)}"
        )

        print(
            f"原始岗位数："
            f"{len(self.all_jobs)}"
        )

        print(
            f"去重后岗位数："
            f"{len(jobs)}"
        )

        print(
            f"接口总岗位数："
            f"{self.total_jobs}"
        )

        return jobs

    # =====================================================
    # 13. 保存最终 JSON
    # =====================================================

    def save(
        self,
        jobs: list[Job],
    ) -> Path:
        """
        保存最终岗位数据。

        输出：

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
            "最终岗位数据已保存：",
            output_file,
        )

        return output_file


# =========================================================
# 单独测试
# =========================================================

if __name__ == "__main__":

    collector = (
        ByteDanceBrowserCollector(

            # -------------------------------------------------
            # 暂时不做关键词过滤
            # -------------------------------------------------

            keyword="",

            # -------------------------------------------------
            # 第一轮测试 5 页
            #
            # 5 × 10 = 最多 50 条
            # -------------------------------------------------

            max_pages=5,

            # -------------------------------------------------
            # True = 后台运行
            # False = 打开浏览器窗口方便观察
            # -------------------------------------------------

            headless=True,
        )
    )

    # =====================================================
    # 开始采集
    # =====================================================

    jobs = collector.collect()

    # =====================================================
    # 保存
    # =====================================================

    output_file = collector.save(
        jobs
    )

    # =====================================================
    # 测试结果
    # =====================================================

    print()
    print("=" * 70)

    print(
        "ByteDance 分页采集测试结束"
    )

    print("=" * 70)

    print(
        f"岗位数量："
        f"{len(jobs)}"
    )

    print(
        f"JSON："
        f"{output_file}"
    )

    print()

    # =====================================================
    # 打印前 10 条
    # =====================================================

    for index, job in enumerate(
        jobs[:10],
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
            f"要求长度："
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
            f"Hash："
            f"{job.content_hash}"
        )

        print(
            "-" * 60
        )