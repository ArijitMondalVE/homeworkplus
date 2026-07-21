"""
AI API Router — Photo upload, answer generation, chat, voice sessions.
"""

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.ai.pipeline import PhotoAnswerPipeline
from app.ai.agents.tutor_agent import TutorAgent
from app.ai.agents.voice_agent import VoiceAgent
from app.config import settings
from app.database.connection import get_db
from app.models.user import User
from app.models.image import Image
from app.models.question import Question
from app.models.answer import Answer
from app.models.chat_history import ChatHistory
from app.schemas.ai_schema import (
    AnswerFeedback,
    AnswerResponse,
    ChatRequest,
    ChatResponse,
    PhotoAnswerRequest,
    PhotoAnswerResponse,
    QuestionCreate,
    QuestionResponse,
)

router = APIRouter(prefix="/ai", tags=["AI Pipeline"])
pipeline = PhotoAnswerPipeline()
tutor = TutorAgent()
voice_agent = VoiceAgent()


@router.post("/upload-image", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a homework image for OCR processing."""
    if file.content_type not in settings.allowed_image_types_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{Path(file.filename or 'image.jpg').suffix}"
    file_path = str(upload_dir / filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create image record
    image = Image(
        user_id=current_user.id,
        filename=filename,
        original_filename=file.filename or filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        processing_status="pending",
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    return {
        "image_id": str(image.id),
        "filename": filename,
        "processing_status": "pending",
        "message": "Image uploaded. Call /ai/solve to process.",
    }


@router.post("/solve", response_model=PhotoAnswerResponse)
async def solve_from_photo(
    payload: PhotoAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoAnswerResponse:
    """Run the full Photo-to-Answer pipeline on an uploaded image."""
    # Get image
    result_img = await db.execute(
        select(Image).where(
            Image.id == payload.image_id, Image.user_id == current_user.id
        )
    )
    image = result_img.scalar_one_or_none()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Update status
    image.processing_status = "processing"
    await db.commit()

    try:
        # Run pipeline
        pipeline_result = await pipeline.process(
            image_path=image.file_path,
            user_id=str(current_user.id),
            language=payload.language,
            include_voice=payload.include_voice,
        )

        if pipeline_result.get("error") and not pipeline_result.get("answer"):
            image.processing_status = "failed"
            image.processing_error = pipeline_result["error"]
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=pipeline_result["error"],
            )

        # Update image record
        image.ocr_text = pipeline_result.get("ocr_text")
        image.latex_text = pipeline_result.get("latex_text")
        image.ocr_engine = pipeline_result.get("ocr_engine")
        image.ocr_confidence = pipeline_result.get("ocr_confidence")
        image.has_math = pipeline_result.get("is_math", False)
        image.has_diagram = pipeline_result.get("has_diagram", False)
        image.enhanced_path = pipeline_result.get("enhanced_path")
        image.processing_status = "done"

        # Create question record
        question = Question(
            user_id=current_user.id,
            content=pipeline_result.get("question_text", ""),
            latex_content=pipeline_result.get("latex_text"),
            question_type=pipeline_result.get("question_type", "general"),
            source_type="image",
            language=payload.language,
            is_solved=True,
        )
        db.add(question)
        await db.flush()

        image.question_id = question.id

        # Create answer record
        import json

        answer = Answer(
            question_id=question.id,
            user_id=current_user.id,
            content=pipeline_result.get("answer", ""),
            latex_content=pipeline_result.get("latex"),
            step_by_step=json.dumps(pipeline_result.get("steps", [])),
            hints=json.dumps(pipeline_result.get("hints", [])),
            explanation=pipeline_result.get("explanation"),
            voice_url=pipeline_result.get("voice_url"),
            llm_provider=pipeline_result.get("llm_provider"),
            tokens_used=pipeline_result.get("tokens_used", 0),
            confidence_score=pipeline_result.get("confidence"),
            rag_sources=json.dumps(pipeline_result.get("rag_sources", [])),
        )
        db.add(answer)

        # Award XP
        current_user.xp_points += 20
        current_user.total_questions_solved += 1

        await db.commit()
        await db.refresh(question)
        await db.refresh(answer)

        return PhotoAnswerResponse(
            question_id=question.id,
            answer_id=answer.id,
            question_text=question.content,
            answer_text=answer.content,
            latex=answer.latex_content,
            steps=pipeline_result.get("steps", []),
            hints=pipeline_result.get("hints", []),
            voice_url=answer.voice_url,
            rag_sources=pipeline_result.get("rag_sources", []),
            confidence=answer.confidence_score,
            processing_time_ms=pipeline_result.get("processing_time_ms", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        image.processing_status = "failed"
        image.processing_error = str(e)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/voice/transcribe", status_code=status.HTTP_200_OK)
async def transcribe_voice(
    file: UploadFile = File(...),
    language: str = Form("en"),
    current_user: User = Depends(get_current_user),
):
    """Transcribe a voice recording."""
    content = await file.read()
    
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"voice_{uuid.uuid4()}{Path(file.filename or 'audio.webm').suffix}"
    file_path = str(upload_dir / filename)

    with open(file_path, "wb") as f:
        f.write(content)

    result = await voice_agent.transcribe(file_path, language=language)
    
    # Optionally clean up the file
    try:
        os.remove(file_path)
    except OSError:
        pass
        
    return result

@router.post("/ask", response_model=PhotoAnswerResponse)
async def ask_text_question(
    payload: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PhotoAnswerResponse:
    """Submit a text question and get an AI answer."""
    from app.ai.agents.rag_agent import RAGAgent
    from app.ai.agents.math_agent import MathAgent
    import json

    rag = RAGAgent()
    math = MathAgent()

    question_type = math.classify_question_type(payload.content)
    rag_sources = rag.search_similar(payload.content, top_k=3)

    llm_result = await tutor.generate_answer(
        question=payload.content,
        rag_sources=rag_sources,
        language=payload.language,
        question_type=question_type,
    )

    question = Question(
        user_id=current_user.id,
        content=payload.content,
        question_type=question_type,
        subject_id=payload.subject_id,
        source_type="text",
        language=payload.language,
        is_solved=True,
    )
    db.add(question)
    await db.flush()

    answer = Answer(
        question_id=question.id,
        user_id=current_user.id,
        content=llm_result.get("answer", ""),
        latex_content=llm_result.get("latex"),
        step_by_step=json.dumps(llm_result.get("steps", [])),
        hints=json.dumps(llm_result.get("hints", [])),
        explanation=llm_result.get("explanation"),
        llm_provider=llm_result.get("llm_provider"),
        tokens_used=llm_result.get("tokens_used", 0),
        confidence_score=llm_result.get("confidence"),
    )
    db.add(answer)
    current_user.xp_points += 20
    current_user.total_questions_solved += 1
    await db.commit()

    return PhotoAnswerResponse(
        question_id=question.id,
        answer_id=answer.id,
        question_text=question.content,
        answer_text=answer.content,
        latex=answer.latex_content,
        steps=llm_result.get("steps", []),
        hints=llm_result.get("hints", []),
        rag_sources=rag_sources,
        confidence=answer.confidence_score,
        processing_time_ms=0,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Multi-turn chat with the AI tutor."""
    result = await tutor.generate_chat_response(
        messages=[m.model_dump() for m in payload.messages],
        session_id=payload.session_id,
        language=payload.language,
    )

    # Store in chat history
    for i, msg in enumerate(payload.messages[-2:]):  # store last 2
        history = ChatHistory(
            user_id=current_user.id,
            session_id=payload.session_id,
            role=msg.role,
            content=msg.content,
            turn_index=len(payload.messages) - 2 + i,
        )
        db.add(history)

    assistant_history = ChatHistory(
        user_id=current_user.id,
        session_id=payload.session_id,
        role="assistant",
        content=result["reply"],
        tokens=result.get("tokens_used", 0),
    )
    db.add(assistant_history)
    await db.commit()

    return ChatResponse(
        session_id=payload.session_id,
        reply=result["reply"],
        tokens_used=result.get("tokens_used", 0),
    )


@router.patch("/answers/{answer_id}/feedback", status_code=status.HTTP_200_OK)
async def submit_answer_feedback(
    answer_id: uuid.UUID,
    payload: AnswerFeedback,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on an AI answer."""
    result = await db.execute(
        select(Answer).where(Answer.id == answer_id, Answer.user_id == current_user.id)
    )
    answer = result.scalar_one_or_none()
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found"
        )

    answer.is_helpful = payload.is_helpful
    answer.rating = payload.rating
    answer.feedback_text = payload.feedback_text
    await db.commit()

    return {"message": "Feedback recorded. Thank you!"}
