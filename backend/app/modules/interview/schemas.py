from pydantic import BaseModel


class InterviewQuestionOut(BaseModel):
    question: str
    category: str  # technical | managerial | hr
    star_hint: str | None = None
    strategy: str | None = None
    sample_answer: str | None = None
    pitfalls: str | None = None


class InterviewPrepOut(BaseModel):
    job_title: str
    company: str
    questions: list[InterviewQuestionOut]
    real_experiences_search_url: str
