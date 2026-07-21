"""Image model — uploaded homework images processed by OCR pipeline."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer)  # bytes
    mime_type: Mapped[str] = mapped_column(String(100))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    # OCR Processing
    ocr_text: Mapped[str | None] = mapped_column(Text)
    latex_text: Mapped[str | None] = mapped_column(Text)
    ocr_engine: Mapped[str | None] = mapped_column(String(50))  # easyocr, paddleocr
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    has_math: Mapped[bool] = mapped_column(Boolean, default=False)
    has_diagram: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pipeline status
    processing_status: Mapped[str] = mapped_column(
        String(30), default="pending"
    )  # pending, processing, done, failed
    processing_error: Mapped[str | None] = mapped_column(Text)
    enhanced_path: Mapped[str | None] = mapped_column(String(500))  # OpenCV-enhanced version

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    question: Mapped["Question"] = relationship("Question", back_populates="images")  # type: ignore
