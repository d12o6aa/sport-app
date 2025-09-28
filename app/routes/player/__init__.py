# app/routes/player/__init__.py
from flask import Blueprint

# تعريف Blueprint للاعبين
athlete_bp = Blueprint("athlete", __name__, template_folder="../../templates/athlete")

# استيراد باقي الملفات عشان يتسجلوا جوه الـ blueprint
from . import readiness_scores, views, goals, schedule, progress,athlete, plans, dashboard, workouts,health, readiness_scores, log_activity, track_progress, integrations,book_sessions,communication,view_plans , training_plans,subscriptions
