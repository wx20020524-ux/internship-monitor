from pathlib import Path

from playwright.sync_api import sync_playwright


TARGET_URL = (
    "https://jobs.bytedance.com/"
    "campus/position?type=3"
)


OUTPUT_FILE = (
    Path("data")
    / "bytedance_raw_response.json"
)


def main():
    print("=" * 60)
    print("ByteDance 浏览器接口探测")
    print("=" * 60)

    captured = {
        "count": 0,
        "saved": False,
    }

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
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

        # -------------------------------------------------
        # 监听所有岗位搜索接口响应
        # -------------------------------------------------

        def handle_response(response):

            if (
                "/api/v1/search/job/posts"
                not in response.url
            ):
                return

            captured["count"] += 1

            print()
            print("=" * 60)
            print(
                "捕获到 ByteDance 岗位搜索接口"
            )
            print("=" * 60)

            print(
                "HTTP：",
                response.status,
            )

            print(
                "URL：",
                response.url,
            )

            print(
                "请求方法：",
                response.request.method,
            )

            print()
            print("请求体：")

            try:

                print(
                    response.request.post_data
                )

            except Exception:

                print(
                    "无法读取请求体"
                )

            print()
            print("响应内容：")

            try:

                data = response.json()

                print(
                    "code =",
                    data.get("code"),
                )

                data_section = (
                    data.get("data")
                    or {}
                )

                posts = (
                    data_section.get(
                        "job_post_list"
                    )
                    or []
                )

                total = (
                    data_section.get(
                        "count",
                        0,
                    )
                )

                print(
                    "岗位数量：",
                    len(posts),
                )

                print(
                    "接口总数：",
                    total,
                )

                # -----------------------------------------
                # 保存原始接口响应
                # -----------------------------------------

                OUTPUT_FILE.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                import json

                with OUTPUT_FILE.open(
                    "w",
                    encoding="utf-8",
                ) as file:

                    json.dump(
                        data,
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )

                captured["saved"] = True

                print()
                print(
                    "原始响应已保存：",
                    OUTPUT_FILE,
                )

                # -----------------------------------------
                # 打印前 3 个岗位
                # -----------------------------------------

                for index, job in enumerate(
                    posts[:3],
                    start=1,
                ):

                    print()
                    print(
                        f"【岗位 {index}】"
                    )

                    print(
                        "ID：",
                        job.get("id"),
                    )

                    print(
                        "标题：",
                        job.get("title"),
                    )

                    print(
                        "描述长度：",
                        len(
                            job.get(
                                "description",
                                "",
                            )
                            or ""
                        ),
                    )

                    print(
                        "要求长度：",
                        len(
                            job.get(
                                "requirement",
                                "",
                            )
                            or ""
                        ),
                    )

            except Exception as error:

                print(
                    "响应不是 JSON：",
                    error,
                )

                try:

                    print(
                        response.text()[:3000]
                    )

                except Exception:

                    pass

        page.on(
            "response",
            handle_response,
        )

        # -------------------------------------------------
        # 打开官方招聘页面
        # -------------------------------------------------

        print()
        print(
            "正在打开："
            f"{TARGET_URL}"
        )

        try:

            page.goto(
                TARGET_URL,
                wait_until="domcontentloaded",
                timeout=60_000,
            )

        except Exception as error:

            print()
            print(
                "页面打开失败：",
                error,
            )

            browser.close()
            return

        print(
            "页面已打开"
        )

        # -------------------------------------------------
        # 给官方 JS 一些时间执行
        # -------------------------------------------------

        print(
            "等待官方页面加载和接口请求..."
        )

        page.wait_for_timeout(
            10_000
        )

        # -------------------------------------------------
        # 截图用于调试
        # -------------------------------------------------

        screenshot_path = (
            Path("data")
            / "bytedance_probe.png"
        )

        page.screenshot(
            path=screenshot_path,
            full_page=True,
        )

        print(
            "页面截图已保存：",
            screenshot_path,
        )

        # -------------------------------------------------
        # 结果
        # -------------------------------------------------

        print()
        print("=" * 60)
        print("探测完成")
        print("=" * 60)

        print(
            "捕获搜索接口次数：",
            captured["count"],
        )

        print(
            "是否保存原始响应：",
            captured["saved"],
        )

        browser.close()


if __name__ == "__main__":
    main()