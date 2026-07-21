"""Embedding model — tracks ChromaDB vector embedding metadata."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    chroma_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(100), default="all-MiniLM-L6-v2")
    embedding_dim: Mapped[int] = mapped_column(Integer, default=384)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
