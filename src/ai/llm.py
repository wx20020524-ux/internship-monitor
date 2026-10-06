import os

import httpx
from dotenv import load_dotenv


load_dotenv()


LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()


def chat_with_llm(
    prompt: str,
    temperature: float = 0.2,
    timeout: float = 120.0,
) -> str:
    """
    调用阿里云百炼 OpenAI-compatible Chat Completions API。
    """

    # 1. 检查配置
    if not LLM_BASE_URL:
        raise ValueError("未配置 LLM_BASE_URL，请检查 .env")

    if not LLM_API_KEY:
        raise ValueError("未配置 LLM_API_KEY，请检查 .env")

    if not LLM_MODEL:
        raise ValueError("未配置 LLM_MODEL，请检查 .env")

    # 2. 拼接真正的请求地址
    url = f"{LLM_BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"LLM API 请求失败：HTTP {error.response.status_code}\n"
            f"响应内容：{error.response.text}"
        ) from error

    except httpx.RequestError as error:
        raise RuntimeError(
            f"LLM 网络请求失败：{error}"
        ) from error

    choices = data.get("choices")

    if not choices:
        raise RuntimeError(
            f"模型返回结果中不存在 choices：{data}"
        )

    message = choices[0].get("message", {})
    content = message.get("content")

    if not content:
        raise RuntimeError(
            f"模型返回结果中不存在 content：{data}"
        )

    return content.strip()