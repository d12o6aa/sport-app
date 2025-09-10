from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, WorkoutLog, HealthRecord, AthleteGoal

from . import coach_bp

# Helper function to check if user is a coach
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# Assessments and reports dashboard
@coach_bp.route("/assessments_reports", methods=["GET"])
@jwt_required()
def assessments_reports():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/assessments_reports.html", athletes=athletes)

# Generate report
@coach_bp.route("/athlete/<int:athlete_id>/generate_report", methods=["GET"])
@jwt_required()
def generate_report(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    range_param = request.args.get("range", "month")
    end_date = datetime.utcnow()
    if range_param == "week":
        start_date = end_date - timedelta(days=7)
    elif range_param == "3months":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=30)

    data = {
        "total_sessions": WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).count(),
        "compliance": 0,
        "avg_performance": 0,
        "weight_change": 0,
        "goals": []
    }

    total_planned = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).count()
    completed_logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date,
        WorkoutLog.compliance_status == "completed"
    ).count()
    data["compliance"] = round((completed_logs / total_planned * 100) if total_planned > 0 else 0, 1)

    performance_logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).all()
    if performance_logs:
        data["avg_performance"] = round(sum(log.metrics.get("performance_score", 0) for log in performance_logs) / len(performance_logs), 1)

    weight_logs = HealthRecord.query.filter(
        HealthRecord.athlete_id == athlete_id,
        HealthRecord.recorded_at >= start_date,
        HealthRecord.recorded_at <= end_date,
        HealthRecord.weight.isnot(None)
    ).order_by(HealthRecord.recorded_at).all()
    if len(weight_logs) >= 2:
        data["weight_change"] = weight_logs[-1].weight - weight_logs[0].weight

    goals = AthleteGoal.query.filter_by(athlete_id=athlete_id).all()
    data["goals"] = [
        {
            "id": goal.id,
            "description": goal.description,
            "target_value": goal.target_value,
            "current_value": goal.current_value,
            "status": goal.status
        } for goal in goals
    ]

    return jsonify(data)

# Set new goal
@coach_bp.route("/athlete/<int:athlete_id>/set_goal", methods=["POST"])
@jwt_required()
def set_goal(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.form
    description = data.get("description")
    target_value = data.get("target_value")
    if not description or not target_value:
        return jsonify({"msg": "Missing required fields"}), 400

    try:
        goal = AthleteGoal(
            athlete_id=athlete_id,
            description=description,
            target_value=float(target_value),
            current_value=0,
            created_at=datetime.utcnow(),
            status="active"
        )
        db.session.add(goal)
        db.session.commit()
        flash("Goal set successfully!", "success")
        return redirect(url_for("assessments_reports.assessments_reports"))
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500