from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from datetime import datetime, date, timedelta
from app import db
from app.models import User, CoachAthlete, Notification, SessionSchedule, WorkoutLog

from . import coach_bp

# Helper function to check if user is a coach
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# Coach dashboard
@coach_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def coach_dashboard():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    today = date.today()
    athletes = (
        db.session.query(User, func.count(WorkoutLog.id))
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .outerjoin(WorkoutLog, WorkoutLog.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .group_by(User)
        .all()
    )

    notifications = Notification.query.filter_by(coach_id=identity, is_read=False).order_by(Notification.sent_at.desc()).limit(5).all()
    sessions = SessionSchedule.query.filter(
        SessionSchedule.coach_id == identity,
        SessionSchedule.scheduled_at >= datetime.combine(today, datetime.min.time()),
        SessionSchedule.scheduled_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).order_by(SessionSchedule.scheduled_at).all()

    return render_template("coach/dashboard.html", athletes=athletes, notifications=notifications, sessions=sessions)


