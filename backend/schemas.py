from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class JobSubmitRequest(BaseModel):
    cv_text: str = Field(..., min_length=1, description="Raw CV content in markdown, text, or JSON format")
    jd_text: str = Field(..., min_length=1, description="Raw job description content")
    title: Optional[str] = Field(default=None, description="Optional friendly label for the job")


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    message: str
    title: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    title: Optional[str] = None
    status: str
    stage: str
    message: str
    created_at: str
    updated_at: str
    iteration: int = 0
    done: bool = False
    best_score: float = 0.0
    overall_score: float = 0.0
    latest_score: Optional[dict[str, Any]] = None
    parsed_profile: dict[str, Any] = Field(default_factory=dict)
    current_cv: str = ""
    critic_feedback: str = ""
    cover_letter: str = ""
    score_history: list[dict[str, Any]] = Field(default_factory=list)
    progress: Optional[dict[str, Any]] = None
    output_dir: Optional[str] = None
    output_files: dict[str, str] = Field(default_factory=dict)
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
