"""
Pydantic schemas for AI endpoints — image upload, answers, voice sessions, chat.
"""
from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Image Upload ──────────────────────────────────────────────────────────────

class ImageUploadResponse(BaseModel):
    image_id: UUID
    filename: str
    processing_status: str
    ocr_text: str | None = None
    latex_text: str | None = None
    has_math: bool = False
    has_diagram: bool = False


# ── Questions ─────────────────────────────────────────────────────────────────

class QuestionCreate(BaseModel):
    content: str = Field(min_length=5, max_length=5000)
    subject_id: UUID | None = None
    language: str = "en"
    source_type: str = "text"


class QuestionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    content: str
    latex_content: str | None = None
    question_type: str
    subject_id: UUID | None = None
    is_solved: bool
    created_at: datetime


# ── Answers ───────────────────────────────────────────────────────────────────

class AnswerResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    question_id: UUID
    content: str
    latex_content: str | None = None
    step_by_step: str | None = None
    hints: str | None = None
    explanation: str | None = None
    voice_url: str | None = None
    llm_provider: str | None = None
    confidence_score: float | None = None
    rag_sources: str | None = None
    created_at: datetime


class AnswerFeedback(BaseModel):
    is_helpful: bool
    rating: int = Field(ge=1, le=5)
    feedback_text: str | None = None


# ── AI Pipeline ───────────────────────────────────────────────────────────────

class PhotoAnswerRequest(BaseModel):
    """Request to run the Photo-to-Answer pipeline on an uploaded image."""
    image_id: UUID
    language: str = "en"
    include_voice: bool = False
    include_whiteboard: bool = False


class PhotoAnswerResponse(BaseModel):
    question_id: UUID
    answer_id: UUID
    question_text: str
    answer_text: str
    latex: str | None = None
    steps: list[str] = []
    hints: list[str] = []
    voice_url: str | None = None
    rag_sources: list[dict[str, Any]] = []
    confidence: float | None = None
    processing_time_ms: int = 0


# ── Chat / Voice ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str
    question_id: UUID | None = None
    language: str = "en"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tokens_used: int = 0


class VoiceSessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    transcript: str | None = None
    response_text: str | None = None
    audio_output_path: str | None = None
    duration_seconds: float | None = None
    created_at: datetime


# ── Progress ──────────────────────────────────────────────────────────────────

class ProgressResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    subject_id: UUID | None = None
    completion_pct: float
    questions_attempted: int
    questions_correct: int
    xp_earned: int
    study_minutes: int


# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    full_name: str
    avatar_url: str | None = None
    xp_points: int
    level: int
