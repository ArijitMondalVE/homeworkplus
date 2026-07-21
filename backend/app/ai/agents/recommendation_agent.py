"""
Recommendation Agent — Suggests personalized practice questions and learning paths.
Progress Agent — Tracks XP, badges, streaks, and achievements.
"""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from loguru import logger


class RecommendationAgent:
    """Suggests next questions and learning paths based on user progress."""

    def get_recommendations(
        self,
        user_data: dict[str, Any],
        recent_questions: list[dict],
        weak_subjects: list[str],
        n: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Generate personalized question recommendations.
        Simple rule-based + can be extended with ML models.
        """
        recommendations = []

        # Prioritize weak subjects
        for subject in weak_subjects[:2]:
            recommendations.append({
                "subject": subject,
                "difficulty": self._next_difficulty(user_data.get("level", 1)),
                "reason": f"Practice {subject} — your weak area",
                "priority": "high",
            })

        # Suggest spaced repetition for older questions
        if recent_questions:
            old_q = recent_questions[-1] if len(recent_questions) > 0 else None
            if old_q:
                recommendations.append({
                    "question_id": old_q.get("id"),
                    "subject": old_q.get("subject"),
                    "reason": "Review from yesterday",
                    "priority": "medium",
                })

        # Fill with general recommendations
        while len(recommendations) < n:
            recommendations.append({
                "subject": "general",
                "difficulty": "medium",
                "reason": "Explore a new topic",
                "priority": "low",
            })

        return recommendations[:n]

    def _next_difficulty(self, level: int) -> str:
        if level < 3:
            return "easy"
        elif level < 7:
            return "medium"
        return "hard"


class ProgressAgent:
    """Tracks learning progress, awards XP, badges, and manages streaks."""

    XP_TABLE = {
        "question_solved": 20,
        "correct_answer": 50,
        "lesson_completed": 100,
        "daily_streak": 30,
        "voice_session": 15,
        "whiteboard_used": 10,
    }

    BADGES = [
        {"name": "First Steps", "icon": "🎯", "condition": "total_questions_solved >= 1", "xp": 50},
        {"name": "Quick Learner", "icon": "⚡", "condition": "total_questions_solved >= 10", "xp": 100},
        {"name": "Problem Solver", "icon": "🧮", "condition": "total_questions_solved >= 50", "xp": 200},
        {"name": "Math Wizard", "icon": "🔮", "condition": "math_questions_solved >= 20", "xp": 250},
        {"name": "On Fire", "icon": "🔥", "condition": "streak_days >= 7", "xp": 150},
        {"name": "Scholar", "icon": "📚", "condition": "total_study_minutes >= 300", "xp": 200},
        {"name": "Voice Champion", "icon": "🎙️", "condition": "voice_sessions >= 10", "xp": 100},
        {"name": "Centurion", "icon": "💯", "condition": "total_questions_solved >= 100", "xp": 500},
    ]

    def calculate_xp_gain(self, action: str, multiplier: float = 1.0) -> int:
        base_xp = self.XP_TABLE.get(action, 0)
        return int(base_xp * multiplier)

    def calculate_level(self, xp: int) -> int:
        """XP curve: level = floor(sqrt(xp / 100)) + 1"""
        import math
        return max(1, int(math.sqrt(xp / 100)) + 1)

    def check_achievements(self, user_stats: dict[str, Any]) -> list[dict[str, Any]]:
        """Return list of newly earned badges based on current stats."""
        earned = []
        for badge in self.BADGES:
            condition = badge["condition"]
            try:
                if eval(condition, {}, user_stats):
                    earned.append(badge)
            except Exception:
                pass
        return earned

    def update_streak(self, last_activity_date: Any, current_date: Any) -> dict[str, int]:
        """Calculate streak days."""
        from datetime import date, timedelta

        if last_activity_date is None:
            return {"streak_days": 1, "streak_bonus_xp": self.XP_TABLE["daily_streak"]}

        if isinstance(last_activity_date, str):
            from datetime import datetime
            last_activity_date = datetime.fromisoformat(last_activity_date).date()

        delta = (current_date - last_activity_date).days
        if delta == 1:
            return {"streak_days": 1, "streak_bonus_xp": self.XP_TABLE["daily_streak"], "continue": True}
        elif delta == 0:
            return {"streak_days": 0, "streak_bonus_xp": 0, "continue": True}
        else:
            return {"streak_days": -1, "streak_bonus_xp": 0, "continue": False}  # streak broken
