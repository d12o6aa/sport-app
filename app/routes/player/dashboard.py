# app/routes/player/dashboard.py
from flask import jsonify, request, render_template

from datetime import date
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, WorkoutLog, HealthRecord, AthleteGoal, TrainingPlan, ReadinessScore, MLInsight, Notification, WorkoutSession, SessionSchedule, PointsLog,AthletePlan
from app.routes.prediction.service import predict_all 

from . import athlete_bp
from datetime import datetime, timedelta

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



@athlete_bp.route("/api/dashboard_data", methods=["GET"])
@jwt_required()
def get_dashboard_data():
    athlete_id = get_jwt_identity()
    
    # 1. Summary Cards Data
    active_goals_count = AthleteGoal.query.filter_by(athlete_id=athlete_id).filter(AthleteGoal.current_value < AthleteGoal.target_value).count()
    
    assigned_plans_count = AthletePlan.query.filter_by(athlete_id=athlete_id).count()

    start_of_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    this_week_workouts_count = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.date >= start_of_week.date()
    ).count()

    readiness_score = ReadinessScore.query.filter_by(athlete_id=athlete_id).order_by(ReadinessScore.date.desc()).first()
    readiness_value = readiness_score.score if readiness_score else "--"
    
    # 2. Recent Workouts Data
    recent_workouts = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(WorkoutLog.date.desc()).limit(5).all()
    
    workouts_data = []
    for w in recent_workouts:
        # Determine intensity based on workout type for a more meaningful value
        intensity = "low"
        if w.session_type and 'cardio' in w.session_type.lower():
            intensity = "high"
        elif w.session_type and 'strength' in w.session_type.lower():
            intensity = "medium"

        workouts_data.append({
            "id": w.id,
            "title": w.session_type,
            "type": w.session_type,
            "date": w.date.isoformat(),
            "intensity": intensity,
            "duration": w.duration
        })
    
    # 3. Active Goals Data
    active_goals = AthleteGoal.query.filter_by(athlete_id=athlete_id).filter(AthleteGoal.current_value < AthleteGoal.target_value).order_by(AthleteGoal.deadline).limit(5).all()
    goals_data = [{
        "id": g.id,
        "title": g.title,
        "due_date": g.deadline.isoformat() if g.deadline else None,
        "progress": round((g.current_value / g.target_value * 100), 1) if g.target_value > 0 else 0
    } for g in active_goals]

    return jsonify({
        "summary": {
            "active_goals": active_goals_count,
            "assigned_plans": assigned_plans_count,
            "week_workouts": this_week_workouts_count,
            "readiness": readiness_value
        },
        "workouts": workouts_data,
        "goals": goals_data
    })

# -------- Dashboard Summary --------
@athlete_bp.route("/summary", methods=["GET"])
@jwt_required()
def athlete_summary():
    user_id = get_jwt_identity()
    athlete = User.query.get(user_id)

    # Goals
    goals = AthleteGoal.query.filter_by(athlete_id=user_id).all()
    active_goals = 0
    for g in goals:

        if g.current_value > 0:
            active_goals += 1
        

    # Plans
    plans = TrainingPlan.query.filter_by(athlete_id=user_id, status="active").count()

    # Workouts this week
    start_week = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    week_workouts = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == user_id,
        WorkoutLog.date >= start_week
    ).count()

    # -------- Readiness (من الـ ML Model) --------
    hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
    last_log = WorkoutLog.query.filter_by(athlete_id=user_id).order_by(WorkoutLog.date.desc()).first()

    features = {
        "heart_rate": hr.heart_rate if (hr and hr.heart_rate is not None) else 0,
        "sleep_hours": hr.sleep_hours if (hr and hr.sleep_hours is not None) else 0,
        "dietary_intake": 0,  
        "training_days_per_week": 0,
        "recovery_days_per_week": 0,
        "Heart_Rate_(HR)": last_log.metrics.get("hr") if (last_log and "hr" in last_log.metrics) else 0,
        "Muscle_Tension_(MT)": last_log.metrics.get("mt") if (last_log and "mt" in last_log.metrics) else 0,
        "Training_Intensity_(TI)": last_log.session_type if (last_log and last_log.session_type) else "Unknown",
        "Training_Duration_(TD)": last_log.duration if (last_log and last_log.duration is not None) else 0,
        "Training_Type_(TT)": last_log.workout_details.get("type") if (last_log and last_log.workout_details) else "Unknown",
        "Time_Interval_(TI)": last_log.workout_details.get("time") if (last_log and last_log.workout_details) else "Unknown",
        "Phase_of_Training_(PT)": "Unknown"
    }


    try:
        readiness_data = predict_all(features)
        readiness_value = (
            readiness_data.get("injury_severity_prediction") or
            readiness_data.get("performance_class") or "--"
        )
    except Exception as e:
        readiness_value = f"Error: {str(e)}"

    # -------- Return --------
    return jsonify({
        "active_goals": active_goals,
        "plans": plans,
        "week_workouts": week_workouts,
        "readiness": readiness_value
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
    



@athlete_bp.route("/readiness", methods=["GET"])
@jwt_required()
def athlete_readiness():
    user_id = get_jwt_identity()

    hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
    last_log = WorkoutLog.query.filter_by(athlete_id=user_id).order_by(WorkoutLog.date.desc()).first()

    features = {
        "heart_rate": hr.heart_rate if hr else 70,
        "sleep_hours": hr.sleep_hours if hr else 7,
        "dietary_intake": 3,
        "training_days_per_week": 4,
        "recovery_days_per_week": 2,
        "Heart_Rate_(HR)": last_log.metrics.get("hr", 75) if last_log else 75,
        "Muscle_Tension_(MT)": last_log.metrics.get("mt", 0.5) if last_log else 0.5,
        "Training_Intensity_(TI)": last_log.session_type if last_log else "Medium",
        "Training_Duration_(TD)": last_log.duration if last_log else 30,
        "Training_Type_(TT)": last_log.workout_details.get("type","Cardio") if last_log else "Cardio",
        "Time_Interval_(TI)": last_log.workout_details.get("time","Morning") if last_log else "Morning",
        "Phase_of_Training_(PT)": "Build"
    }

    try:
        result = predict_all(features)  # استدعاء الموديل مباشرة
    except Exception as e:
        result = {"error": str(e)}

    return jsonify(result)


def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    today = date.today()
    tasks = WorkoutSession.query.filter(
        WorkoutSession.athlete_id == identity,
        WorkoutSession.performed_at >= datetime.combine(today, datetime.min.time()),
        WorkoutSession.performed_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).all()
    notifications = Notification.query.filter_by(athlete_id=identity, is_read=False).order_by(Notification.sent_at.desc()).limit(5).all()
    sessions = SessionSchedule.query.filter(
        SessionSchedule.athlete_id == identity,
        SessionSchedule.scheduled_at >= datetime.combine(today, datetime.min.time()),
        SessionSchedule.scheduled_at < datetime.combine(today + timedelta(days=1), datetime.min.time())
    ).order_by(SessionSchedule.scheduled_at).all()
    points = PointsLog.query.filter_by(athlete_id=identity).order_by(PointsLog.awarded_at.desc()).limit(5).all()
    return render_template("dashboard/athlete_dashboard.html", tasks=tasks, notifications=notifications, sessions=sessions, points=points)