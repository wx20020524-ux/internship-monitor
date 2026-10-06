import json
import os
from typing import Any

from dotenv import load_dotenv

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0").strip()


class RedisCache:
    """Redis 可选缓存封装；Redis 不可用时自动降级，并支持后续重连。"""

    def __init__(self) -> None:
        self._client = None
        self._available = False

    def _ensure_client(self) -> bool:
        if redis is None:
            return False
        if self._client is None:
            try:
                self._client = redis.Redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
            except Exception:
                self._client = None
                return False
        try:
            self._client.ping()
            self._available = True
            return True
        except Exception:
            self._available = False
            return False

    @property
    def available(self) -> bool:
        return self._ensure_client()

    def get_json(self, key: str) -> Any | None:
        if not self._ensure_client():
            return None
        try:
            value = self._client.get(key)
            return json.loads(value) if value else None
        except Exception:
            self._available = False
            return None

    def set_json(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self._ensure_client():
            return False
        try:
            self._client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
            return True
        except Exception:
            self._available = False
            return False

    def delete(self, *keys: str) -> None:
        if not keys or not self._ensure_client():
            return
        try:
            self._client.delete(*keys)
        except Exception:
            self._available = False

    def incr_with_ttl(self, key: str, ttl: int) -> int | None:
        if not self._ensure_client():
            return None
        try:
            value = int(self._client.incr(key))
            if value == 1:
                self._client.expire(key, ttl)
            return value
        except Exception:
            self._available = False
            return None


cache = RedisCache()
