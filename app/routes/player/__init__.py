# app/routes/player/__init__.py
from flask import Blueprint

# تعريف Blueprint للاعبين
athlete_bp = Blueprint("athlete", __name__, template_folder="../../templates/athlete")

# استيراد باقي الملفات عشان يتسجلوا جوه الـ blueprint
# from . import readiness_scores,   schedule, progress, dashboard, health, readiness_scores, log_activity, track_progress, integrations,book_sessions,communication,view_plans , subscriptions

from . import views,goals,athlete, plans,workouts,training_plans,profile,progress,dashboard