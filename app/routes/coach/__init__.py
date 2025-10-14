from flask import Blueprint

coach_bp = Blueprint('coach', __name__)

from . import coach,views,manage_athlete, communication, assessments_reports, dashboard, track_progress, manage_plans, calendar, compliance, select_feedback,create_workout ,give_feedback, progress_tracking
from . import sessions_management