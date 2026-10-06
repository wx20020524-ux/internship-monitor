from datetime import datetime

from pydantic import BaseModel, Field


class Job(BaseModel):
    """整个招聘平台统一使用的岗位模型。"""

    company: str = ""
    source: str = ""

    # 招聘网站自己的岗位 ID
    source_job_id: str = ""

    # 用于判断岗位内容是否发生变化
    content_hash: str = ""

    title: str = ""
    city: str = ""
    country: str = ""

    department: str = ""
    category: str = ""

    salary: str = ""
    education: str = ""
    experience: str = ""

    description: str = ""
    requirements: str = ""

    job_type: str = ""

    publish_time: str = ""
    update_time: str = ""

    source_url: str = ""

    crawl_time: datetime = Field(
        default_factory=datetime.now
    )