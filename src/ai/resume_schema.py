from pydantic import BaseModel, Field
from typing import List


class ResumeProfile(BaseModel):
    education: str = ""
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    target_roles: List[str] = Field(default_factory=list)