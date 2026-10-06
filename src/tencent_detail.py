import time
from typing import Any

import httpx


DETAIL_API_URL = (
    "https://careers.tencent.com/"
    "tencentcareer/api/post/ByPostId"
)


def fetch_tencent_job_detail(
    post_id: str,
) -> dict[str, Any]:
    """
    根据岗位 ID 获取腾讯岗位详情。
    """

    params = {
        "timestamp": str(
            int(time.time() * 1000)
        ),
        "postId": post_id,
        "language": "zh-cn",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
    }

    with httpx.Client(
        headers=headers,
        timeout=20.0,
        follow_redirects=True,
    ) as client:

        response = client.get(
            DETAIL_API_URL,
            params=params,
        )

    print(
        f"详情 API 状态码："
        f"{response.status_code}"
    )

    response.raise_for_status()

    return response.json()
if __name__ == "__main__":
    post_id = "2074746946387623936"

    try:
        data = fetch_tencent_job_detail(
            post_id
        )

        print("\n详情 API 请求成功")

        data_section = data.get(
            "Data",
            {}
        )

        print(
            "\n岗位名称：",
            data_section.get(
                "RecruitPostName",
                ""
            )
        )

        print(
            "\n工作职责："
        )

        print(
            data_section.get(
                "Responsibility",
                ""
            )
        )

        print(
            "\n任职要求："
        )

        print(
            data_section.get(
                "Requirement",
                ""
            )
        )

    except Exception as error:

        print("\n请求失败：")
        print(
            type(error).__name__,
            error
        )