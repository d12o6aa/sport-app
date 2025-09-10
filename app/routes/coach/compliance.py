from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, WorkoutLog

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/compliance", methods=["GET"])
@jwt_required()
def compliance():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    compliance_data = []
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    for athlete in athletes:
        total_logs = WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete.id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).count()
        completed_logs = WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete.id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date,
            WorkoutLog.compliance_status == "completed"
        ).count()
        compliance_rate = round((completed_logs / total_logs * 100) if total_logs > 0 else 0, 1)
        compliance_data.append({
            "athlete_id": athlete.id,
            "name": athlete.name,
            "compliance_rate": compliance_rate,
            "total_logs": total_logs,
            "completed_logs": completed_logs
        })

    return render_template("coach/compliance.html", compliance_data=compliance_data)