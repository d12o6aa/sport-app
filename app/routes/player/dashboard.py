# app/routes/player/dashboard.py
from flask import jsonify, request
from datetime import date
from app import db
from app.models.readiness_scores import ReadinessScore
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.athlete_goals import AthleteGoal
from app.models.training_plan import TrainingPlan
from app.models.workout_log import WorkoutLog
from . import athlete_bp

@athlete_bp.route("/api/dashboard", methods=["GET"])
@jwt_required()
def dashboard_data():
    athlete_id = get_jwt_identity()
    goals_count = AthleteGoal.query.filter_by(athlete_id=athlete_id).count()
    plans_count = TrainingPlan.query.filter_by(athlete_id=athlete_id).count()
    workouts_count = WorkoutLog.query.filter_by(athlete_id=athlete_id).count()

    return jsonify({
        "goals": goals_count,
        "plans": plans_count,
        "workouts": workouts_count
    })


# -------- Dashboard Summary --------
@athlete_bp.route("/athlete/summary", methods=["GET"])
@jwt_required()
def athlete_summary():
    user_id = get_jwt_identity()

    active_goals = AthleteGoal.query.filter_by(athlete_id=user_id).filter(AthleteGoal.deadline >= date.today()).count()
    plans = TrainingPlan.query.filter_by(athlete_id=user_id).count()
    week_workouts = WorkoutLog.query.filter_by(athlete_id=user_id)\
        .filter(WorkoutLog.date >= date.today()).count()
    readiness = db.session.query(ReadinessScore).filter_by(athlete_id=user_id)\
        .order_by(ReadinessScore.date.desc()).first()

    return jsonify({
        "active_goals": active_goals,
        "plans": plans,
        "week_workouts": week_workouts,
        "readiness": readiness.score if readiness else "--"
    })

# -------- Recent Workouts --------
@athlete_bp.route("/athlete/workouts", methods=["GET"])
@jwt_required()
def athlete_workouts():
    user_id = get_jwt_identity()
    limit = int(request.args.get("limit", 5))
    workouts = WorkoutLog.query.filter_by(athlete_id=user_id)\
        .order_by(WorkoutLog.date.desc())\
        .limit(limit).all()

    return jsonify([
        {
            "id": w.id,
            "title": w.title,
            "type": w.type,
            "date": w.date.isoformat(),
            "intensity": w.intensity
        } for w in workouts
    ])

# -------- Active Goals --------
@athlete_bp.route("/athlete/goals", methods=["GET"])
@jwt_required()
def athlete_goals():
    user_id = get_jwt_identity()
    status = request.args.get("status", "active")

    goals = AthleteGoal.query.filter_by(athlete_id=user_id)
    if status == "active":
        goals = goals.filter(AthleteGoal.deadline >= date.today())
    goals = goals.order_by(AthleteGoal.deadline).all()

    return jsonify([
        {
            "id": g.id,
            "title": g.title,
            "due_date": g.deadline.isoformat() if g.deadline else None,
            "progress": (g.current_value / g.target_value * 100) if g.target_value else 0
        } for g in goals
    ])