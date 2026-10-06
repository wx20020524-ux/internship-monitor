from src.collectors.base import BaseCollector
from src.collectors.bytedance_browser import (
    ByteDanceBrowserCollector,
)
from src.collectors.tencent import TencentCollector


# =========================================================
# 公司采集器注册表
# =========================================================

COLLECTOR_REGISTRY: dict[
    str,
    type[BaseCollector],
] = {
    "tencent": TencentCollector,
    "bytedance": ByteDanceBrowserCollector,
}


# =========================================================
# 获取采集器
# =========================================================

def get_collector(
    company: str,
    **kwargs,
) -> BaseCollector:
    """
    根据公司名称获取采集器。
    """

    collector_class = (
        COLLECTOR_REGISTRY.get(
            company
        )
    )

    if collector_class is None:

        raise ValueError(
            f"暂不支持公司：{company}"
        )

    return collector_class(
        **kwargs
    )