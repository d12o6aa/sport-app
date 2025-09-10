from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, SessionSchedule, TrainingPlan

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/calendar", methods=["GET"])
@jwt_required()
def calendar():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    return render_template("coach/calendar.html")

@coach_bp.route("/calendar_events", methods=["GET"])
@jwt_required()
def calendar_events():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    sessions = (
        db.session.query(SessionSchedule)
        .join(CoachAthlete, CoachAthlete.athlete_id == SessionSchedule.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    plans = (
        db.session.query(TrainingPlan)
        .join(CoachAthlete, CoachAthlete.athlete_id == TrainingPlan.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )

    events = []
    for session in sessions:
        events.append({
            "title": f"{session.title} ({session.athlete.name})",
            "start": session.scheduled_at.isoformat(),
            "end": session.scheduled_at.isoformat(),
            "color": "green" if session.type == "virtual" else "blue"
        })
    for plan in plans:
        events.append({
            "title": f"{plan.title} ({plan.athlete.name})",
            "start": plan.start_date.isoformat(),
            "end": plan.end_date.isoformat() if plan.end_date else None,
            "color": "purple"
        })

    return jsonify(events)