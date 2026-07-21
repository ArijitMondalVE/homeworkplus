"""
Dashboard API — user stats, recent activity, leaderboard, notifications.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database.connection import get_db
from app.models.user import User
from app.models.question import Question
from app.models.answer import Answer
from app.models.achievement import Achievement, Leaderboard
from app.models.notification import Notification
from app.models.progress import Progress

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive dashboard statistics for the current user."""
    # Recent questions
    recent_qs_result = await db.execute(
        select(Question)
        .where(Question.user_id == current_user.id)
        .order_by(desc(Question.created_at))
        .limit(5)
    )
    recent_questions = recent_qs_result.scalars().all()

    # Achievements count
    achievements_result = await db.execute(
        select(func.count()).where(Achievement.user_id == current_user.id)
    )
    achievement_count = achievements_result.scalar() or 0

    # Notifications (unread)
    notif_result = await db.execute(
        select(func.count()).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    unread_notifications = notif_result.scalar() or 0

    return {
        "user": {
            "id": str(current_user.id),
            "username": current_user.username,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
            "xp_points": current_user.xp_points,
            "level": current_user.level,
            "streak_days": current_user.streak_days,
        },
        "stats": {
            "total_questions_solved": current_user.total_questions_solved,
            "total_study_minutes": current_user.total_study_minutes,
            "achievement_count": achievement_count,
            "xp_to_next_level": max(0, ((current_user.level) ** 2) * 100 - current_user.xp_points),
        },
        "recent_questions": [
            {
                "id": str(q.id),
                "content": q.content[:100],
                "question_type": q.question_type,
                "is_solved": q.is_solved,
                "created_at": q.created_at.isoformat(),
            }
            for q in recent_questions
        ],
        "unread_notifications": unread_notifications,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    period: str = "weekly",
    subject_id: str | None = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get top users by XP for a given period."""
    query = (
        select(User)
        .where(User.is_active == True)
        .order_by(desc(User.xp_points))
        .limit(limit)
    )
    result = await db.execute(query)
    users = result.scalars().all()

    entries = [
        {
            "rank": i + 1,
            "user_id": str(u.id),
            "username": u.username,
            "full_name": u.full_name,
            "avatar_url": u.avatar_url,
            "xp_points": u.xp_points,
            "level": u.level,
            "is_current_user": u.id == current_user.id,
        }
        for i, u in enumerate(users)
    ]

    return {"period": period, "entries": entries}


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the current user."""
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.is_read == False)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "title": n.title,
            "body": n.body,
            "type": n.notification_type,
            "is_read": n.is_read,
            "action_url": n.action_url,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    from fastapi import HTTPException
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}


@router.delete("/questions/clear")
async def clear_recent_questions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all questions (recent activity) for the current user."""
    from sqlalchemy import delete
    await db.execute(delete(Question).where(Question.user_id == current_user.id))
    await db.commit()
    return {"message": "Recent activity cleared successfully"}
