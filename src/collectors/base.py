from abc import ABC, abstractmethod

from src.models import Job


class BaseCollector(ABC):
    """
    所有公司岗位采集器的统一基类。
    """

    COMPANY_NAME: str = ""
    SOURCE_NAME: str = ""

    def __init__(
        self,
        keyword: str = "",
        max_pages: int = 1,
    ):
        self.keyword = keyword
        self.max_pages = max_pages

    @abstractmethod
    def collect(self) -> list[Job]:
        """
        采集岗位。

        所有公司采集器都必须实现这个方法。
        """
        raise NotImplementedError