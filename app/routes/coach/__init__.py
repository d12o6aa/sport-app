from flask import Blueprint

coach_bp = Blueprint('coach', __name__)

from . import coach,views,manage_athlete, communication, assessments_reports, dashboard, track_progress, manage_plans, workout_list, my_athletes, all_plans, calendar, athlete_details, compliance, select_feedback,create_workout ,give_feedback, progress_tracking,view_feedback