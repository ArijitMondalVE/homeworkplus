"""Answer model — AI-generated answers to student questions."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    latex_content: Mapped[str | None] = mapped_column(Text)
    step_by_step: Mapped[str | None] = mapped_column(Text)  # JSON array of steps
    hints: Mapped[str | None] = mapped_column(Text)  # JSON array of hints
    explanation: Mapped[str | None] = mapped_column(Text)
    voice_url: Mapped[str | None] = mapped_column(String(500))  # TTS audio file
    whiteboard_data: Mapped[str | None] = mapped_column(Text)  # Fabric.js JSON

    # AI Metadata
    llm_provider: Mapped[str | None] = mapped_column(String(50))  # openai, anthropic
    llm_model: Mapped[str | None] = mapped_column(String(100))
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    rag_sources: Mapped[str | None] = mapped_column(Text)  # JSON list of source chunks

    # Feedback
    is_helpful: Mapped[bool | None] = mapped_column(Boolean)
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5 stars
    feedback_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    question: Mapped["Question"] = relationship("Question", back_populates="answers")  # type: ignore
