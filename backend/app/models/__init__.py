"""
All 16 SQLAlchemy ORM models for HomeworkPlus.
Imports all models to ensure they are registered with Base.metadata.
"""
from app.models.user import User
from app.models.subject import Subject
from app.models.lesson import Lesson
from app.models.question import Question
from app.models.answer import Answer
from app.models.image import Image
from app.models.voice_session import VoiceSession
from app.models.canvas_session import CanvasSession
from app.models.achievement import Achievement
from app.models.reward import Reward
from app.models.leaderboard import Leaderboard
from app.models.chat_history import ChatHistory
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.progress import Progress
from app.models.notification import Notification
from app.models.subscription import Subscription

all_models = [
    User, Subject, Lesson, Question, Answer, Image,
    VoiceSession, CanvasSession, Achievement, Reward,
    Leaderboard, ChatHistory, Document, Embedding,
    Progress, Notification, Subscription,
]

__all__ = [
    "User", "Subject", "Lesson", "Question", "Answer", "Image",
    "VoiceSession", "CanvasSession", "Achievement", "Reward",
    "Leaderboard", "ChatHistory", "Document", "Embedding",
    "Progress", "Notification", "Subscription", "all_models",
]
