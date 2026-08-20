from pydantic import BaseModel


class SkillGapOut(BaseModel):
    skill: str
    priority: str
    reason: str
    target_job_title: str
    current_evidence: str
    resources: list[str]
    project_suggestion: str
    estimated_days: int


class RoadmapOut(BaseModel):
    immediate: list[str]
    week_1: list[str]
    week_2: list[str]
    month_1: list[str]
