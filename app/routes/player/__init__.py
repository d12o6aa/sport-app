# app/routes/player/__init__.py
from flask import Blueprint

# تعريف Blueprint للاعبين
athlete_bp = Blueprint("athlete", __name__, template_folder="../../templates/athlete")

# استيراد باقي الملفات عشان يتسجلوا جوه الـ blueprint
from . import views, goals, schedule, progress,athlete
