"""
Celery background tasks for async AI processing.
"""
from __future__ import annotations

import os
os.environ["FLAGS_use_onednn"] = "0"
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
from loguru import logger
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.tasks.process_image", max_retries=3)
def process_image(self, image_id: str, user_id: str, language: str = "en"):
    """
    Async task: Run the Photo-to-Answer pipeline on an image.
    Called after upload to process in background.
    """
    import asyncio
    from app.ai.pipeline import PhotoAnswerPipeline

    logger.info(f"[Task] Processing image {image_id} for user {user_id}")

    try:
        pipeline = PhotoAnswerPipeline()
        result = asyncio.run(
            pipeline.process(
                image_path=f"./uploads/{image_id}",
                user_id=user_id,
                language=language,
            )
        )
        logger.info(f"[Task] Image {image_id} processed successfully")
        return result
    except Exception as exc:
        logger.error(f"[Task] Image processing failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.tasks.ingest_document")
def ingest_document(document_id: str, file_path: str, subject: str | None = None):
    """
    Async task: Chunk and ingest a document into ChromaDB for RAG.
    """
    import asyncio
    from pathlib import Path
    from app.ai.agents.rag_agent import RAGAgent

    logger.info(f"[Task] Ingesting document {document_id}")

    try:
        # Read document content
        text = Path(file_path).read_text(encoding="utf-8", errors="ignore")

        # Simple chunking (1000 chars with 200 overlap)
        chunk_size = 1000
        overlap = 200
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)

        metadata = [
            {"document_id": document_id, "subject": subject or "general", "chunk_index": i}
            for i in range(len(chunks))
        ]

        rag = RAGAgent()
        success = rag.ingest_document(chunks=chunks, metadata=metadata)

        logger.info(f"[Task] Ingested {len(chunks)} chunks for document {document_id}")
        return {"document_id": document_id, "chunks_ingested": len(chunks), "success": success}
    except Exception as e:
        logger.error(f"[Task] Document ingestion failed: {e}")
        return {"document_id": document_id, "error": str(e)}


@celery_app.task(name="app.workers.tasks.generate_tts")
def generate_tts(text: str, output_path: str, language: str = "en"):
    """Async TTS generation task."""
    import asyncio
    from app.ai.agents.voice_agent import VoiceAgent

    logger.info(f"[Task] Generating TTS for {len(text)} chars")
    va = VoiceAgent()
    result = asyncio.run(va.text_to_speech(text, output_path, language))
    return {"output_path": result}
