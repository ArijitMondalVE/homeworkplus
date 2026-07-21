"""Question model — homework questions submitted by students."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True
    )

    # Content
    title: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    latex_content: Mapped[str | None] = mapped_column(Text)  # Math equations in LaTeX
    language: Mapped[str] = mapped_column(String(10), default="en")

    # Classification
    question_type: Mapped[str] = mapped_column(
        String(50), default="general"
    )  # math, physics, chemistry, biology, general
    difficulty: Mapped[str | None] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(
        String(30), default="text"
    )  # text, image, voice

    # Metadata
    is_solved: Mapped[bool] = mapped_column(Boolean, default=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subject: Mapped["Subject"] = relationship("Subject", back_populates="questions")  # type: ignore
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="questions")  # type: ignore
    answers: Mapped[list] = relationship("Answer", back_populates="question")
    images: Mapped[list] = relationship("Image", back_populates="question")
