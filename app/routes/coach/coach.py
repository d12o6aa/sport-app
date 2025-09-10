# coach.py

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, TrainingPlan, WorkoutLog, Feedback, Message, ActivityLog, AthleteProgress, HealthRecord, ReadinessScore, InjuryRecord, AthletePlan, AthleteProfile, WorkoutSession, NutritionPlan
from werkzeug.security import generate_password_hash

from . import coach_bp

# Helper function to check if user is a coach
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# Get athlete progress data
@coach_bp.route("/athlete/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_athlete_progress(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    range_param = request.args.get("range", "month")
    progress_type = request.args.get("type", "performance")
    
    end_date = datetime.utcnow()
    if range_param == "week":
        start_date = end_date - timedelta(days=7)
    elif range_param == "3months":
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=30)

    data = {
        "total_sessions": 0,
        "compliance": 0,
        "compliance_label": "N/A",
        "avg_readiness": 0,
        "injury_alerts": 0,
        "labels": [],
        "values": [],
        "secondary_values": [],
        "logs": [],
        "activities": []
    }

    data["total_sessions"] = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).count()

    total_planned = AthletePlan.query.filter(
        AthletePlan.athlete_id == athlete_id,
        AthletePlan.assigned_at >= start_date,
        AthletePlan.assigned_at <= end_date
    ).count()
    completed_logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date,
        WorkoutLog.compliance_status == "completed"
    ).count()
    data["compliance"] = round((completed_logs / total_planned * 100) if total_planned > 0 else 0, 1)
    data["compliance_label"] = "Excellent" if data["compliance"] >= 90 else "Good" if data["compliance"] >= 70 else "Needs Improvement"

    readiness_scores = ReadinessScore.query.filter(
        ReadinessScore.athlete_id == athlete_id,
        ReadinessScore.date >= start_date,
        ReadinessScore.date <= end_date
    ).all()
    if readiness_scores:
        data["avg_readiness"] = round(sum(rs.score for rs in readiness_scores) / len(readiness_scores) / 10, 1)

    data["injury_alerts"] = InjuryRecord.query.filter(
        InjuryRecord.athlete_id == athlete_id,
        InjuryRecord.reported_at >= start_date,
        InjuryRecord.reported_at <= end_date,
        InjuryRecord.severity.in_(["moderate", "severe"])
    ).count()

    if progress_type == "weight":
        progress_data = HealthRecord.query.filter(
            HealthRecord.athlete_id == athlete_id,
            HealthRecord.recorded_at >= start_date,
            HealthRecord.recorded_at <= end_date,
            HealthRecord.weight.isnot(None)
        ).order_by(HealthRecord.recorded_at).all()
        data["labels"] = [pd.recorded_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.weight for pd in progress_data]
        data["secondary_values"] = [rs.score for rs in readiness_scores] if readiness_scores else []
    elif progress_type == "nutrition":
        progress_data = HealthRecord.query.filter(
            HealthRecord.athlete_id == athlete_id,
            HealthRecord.recorded_at >= start_date,
            HealthRecord.recorded_at <= end_date,
            HealthRecord.calories_intake.isnot(None)
        ).order_by(HealthRecord.recorded_at).all()
        data["labels"] = [pd.recorded_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.calories_intake for pd in progress_data]
        data["secondary_values"] = [rs.score for rs in readiness_scores] if readiness_scores else []
    else:
        progress_data = WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.logged_at >= start_date,
            WorkoutLog.logged_at <= end_date
        ).order_by(WorkoutLog.logged_at).all()
        data["labels"] = [pd.logged_at.strftime("%Y-%m-%d") for pd in progress_data]
        data["values"] = [pd.metrics.get("performance_score", 0) for pd in progress_data]
        data["secondary_values"] = [rs.score for rs in readiness_scores] if readiness_scores else []

    logs = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.logged_at >= start_date,
        WorkoutLog.logged_at <= end_date
    ).order_by(WorkoutLog.logged_at.desc()).all()
    data["logs"] = [
        {
            "id": log.id,
            "date": log.date.strftime("%Y-%m-%d"),
            "type": log.session_type,
            "details": log.workout_details.get("description", "N/A"),
            "metric": log.metrics.get("key_metric", "N/A"),
            "status": log.compliance_status.capitalize(),
            "status_color": "success" if log.compliance_status == "completed" else "warning" if log.compliance_status == "partial" else "danger"
        }
        for log in logs
    ]

    activities = ActivityLog.query.filter(
        ActivityLog.user_id == athlete_id,
        ActivityLog.created_at >= start_date,
        ActivityLog.created_at <= end_date
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()
    data["activities"] = [
        {
            "time": (datetime.utcnow() - act.created_at).total_seconds() // 60,
            "color": "success" if "completed" in act.action.lower() else "danger" if "injury" in act.action.lower() else "primary",
            "text": act.action
        }
        for act in activities
    ]

    return jsonify(data)

# Get athlete training plans
@coach_bp.route("/athlete/<int:athlete_id>/plans", methods=["GET"])
@jwt_required()
def get_athlete_plans(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id, coach_id=identity).all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "start": p.start_date.isoformat(),
            "end": p.end_date.isoformat(),
            "status": p.status
        }
        for p in plans
    ])

# Create a new training plan
@coach_bp.route("/create_plan", methods=["GET", "POST"])
@jwt_required()
def create_plan():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.get_json()
        athlete_id = data.get("athlete_id")
        link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
        if not link:
            return jsonify({"msg": "Not your athlete"}), 403

        try:
            plan = TrainingPlan(
                athlete_id=athlete_id,
                coach_id=identity,
                title=data.get("title"),
                description=data.get("description"),
                start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d"),
                end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d"),
                status="active",
                duration_weeks=((datetime.strptime(data.get("end_date"), "%Y-%m-%d") - 
                                datetime.strptime(data.get("start_date"), "%Y-%m-%d")).days // 7)
            )
            db.session.add(plan)
            db.session.flush()

            # Add workout sessions
            for session in data.get("sessions", []):
                workout_session = WorkoutSession(
                    athlete_id=athlete_id,
                    plan_id=plan.id,
                    name=session.get("name"),
                    type=session.get("type"),
                    duration=session.get("duration"),
                    performed_at=datetime.utcnow()
                )
                db.session.add(workout_session)

            # Add nutrition plan
            if data.get("nutrition"):
                nutrition = data["nutrition"]
                nutrition_plan = NutritionPlan(
                    athlete_id=athlete_id,
                    plan_id=plan.id,
                    calories_intake=nutrition.get("calories_intake"),
                    notes=nutrition.get("notes"),
                    created_at=datetime.utcnow()
                )
                db.session.add(nutrition_plan)


            db.session.commit()
            return jsonify({"msg": "Plan created successfully"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/create_plan.html", athletes=athletes)

# Edit a training plan
@coach_bp.route("/plans/<int:plan_id>/edit", methods=["GET", "POST"])
@jwt_required()
def edit_plan(plan_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first_or_404()

    if request.method == "POST":
        data = request.get_json()
        try:
            plan.title = data.get("title", plan.title)
            plan.description = data.get("description", plan.description)
            plan.start_date = datetime.strptime(data.get("start_date"), "%Y-%m-%d") if data.get("start_date") else plan.start_date
            plan.end_date = datetime.strptime(data.get("end_date"), "%Y-%m-%d") if data.get("end_date") else plan.end_date
            plan.status = data.get("status", plan.status)
            plan.duration_weeks = ((plan.end_date - plan.start_date).days // 7) if plan.start_date and plan.end_date else plan.duration_weeks

            # Update workout sessions
            if data.get("sessions"):
                WorkoutSession.query.filter_by(plan_id=plan.id).delete()
                for session in data["sessions"]:
                    workout_session = WorkoutSession(
                        athlete_id=plan.athlete_id,
                        plan_id=plan.id,
                        name=session.get("name"),
                        type=session.get("type"),
                        duration=session.get("duration"),
                        performed_at=datetime.utcnow()
                    )
                    db.session.add(workout_session)

            # Update nutrition plan
            if data.get("nutrition"):
                nutrition = data["nutrition"]

                # نجيب الـ nutrition plan المرتبط بالـ plan ده
                nutrition_plan = NutritionPlan.query.filter_by(plan_id=plan.id, athlete_id=plan.athlete_id).first()

                if nutrition_plan:
                    nutrition_plan.calories_intake = nutrition.get("calories_intake", nutrition_plan.calories_intake)
                    nutrition_plan.notes = nutrition.get("notes", nutrition_plan.notes)
                else:
                    nutrition_plan = NutritionPlan(
                        athlete_id=plan.athlete_id,
                        plan_id=plan.id,
                        calories_intake=nutrition.get("calories_intake"),
                        notes=nutrition.get("notes"),
                        created_at=datetime.utcnow()
                    )
                    db.session.add(nutrition_plan)


            db.session.commit()
            return jsonify({"msg": "Plan updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    sessions = WorkoutSession.query.filter_by(plan_id=plan_id).all()
    health_record = HealthRecord.query.filter_by(athlete_id=plan.athlete_id).order_by(HealthRecord.recorded_at.desc()).first()
    return render_template("coach/edit_plan.html", plan=plan, sessions=sessions, nutrition=health_record)


@coach_bp.route("/plans/edit", methods=["GET"])
@jwt_required()
def edit_plans_list():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return redirect(url_for("auth.login"))

    plans = TrainingPlan.query.filter_by(coach_id=identity).all()
    return render_template("coach/manage_plans.html", plans=plans)

# Delete a training plan
@coach_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first_or_404()
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"msg": "Plan deleted successfully"}), 200

# Duplicate a training plan
@coach_bp.route("/plans/<int:plan_id>/duplicate", methods=["POST"])
@jwt_required()
def duplicate_plan(plan_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first_or_404()
    try:
        new_plan = TrainingPlan(
            athlete_id=plan.athlete_id,
            coach_id=plan.coach_id,
            title=plan.title + " (Copy)",
            description=plan.description,
            start_date=plan.start_date,
            end_date=plan.end_date,
            status=plan.status,
            duration_weeks=plan.duration_weeks
        )
        db.session.add(new_plan)
        db.session.flush()

        sessions = WorkoutSession.query.filter_by(plan_id=plan.id).all()
        for session in sessions:
            new_session = WorkoutSession(
                athlete_id=session.athlete_id,
                plan_id=new_plan.id,
                name=session.name,
                type=session.type,
                duration=session.duration,
                performed_at=session.performed_at
            )
            db.session.add(new_session)

        health_record = HealthRecord.query.filter_by(athlete_id=plan.athlete_id).order_by(HealthRecord.recorded_at.desc()).first()
        if health_record:
            new_health_record = HealthRecord(
                athlete_id=plan.athlete_id,
                recorded_at=datetime.utcnow(),
                calories_intake=health_record.calories_intake,
                notes=health_record.notes
            )
            db.session.add(new_health_record)

        db.session.commit()
        return jsonify({"msg": "Plan duplicated", "id": new_plan.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Send message to athlete
@coach_bp.route("/athlete/<int:athlete_id>/send_message", methods=["GET", "POST"])
@jwt_required()
def send_message(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    if request.method == "POST":
        data = request.form
        message = Message(
            sender_id=identity,
            receiver_id=athlete_id,
            content=data.get("content"),
            sent_at=datetime.utcnow(),
            is_read=False
        )
        db.session.add(message)
        db.session.commit()
        flash("Message sent successfully!", "success")
        return redirect(url_for("coach.view_messages", athlete_id=athlete_id))

    athlete = User.query.get_or_404(athlete_id)
    return render_template("coach/send_message.html", athlete=athlete)

# View messages with athlete
@coach_bp.route("/athlete/<int:athlete_id>/messages", methods=["GET"])
@jwt_required()
def view_messages(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    messages = Message.query.filter(
        ((Message.sender_id == identity) & (Message.receiver_id == athlete_id)) |
        ((Message.sender_id == athlete_id) & (Message.receiver_id == identity))
    ).order_by(Message.sent_at.desc()).all()

    athlete = User.query.get_or_404(athlete_id)
    return render_template("coach/view_messages.html", athlete=athlete, messages=messages)


# View workout log details
@coach_bp.route("/logs/<int:log_id>", methods=["GET"])
@jwt_required()
def view_log(log_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    log = WorkoutLog.query.get_or_404(log_id)
    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=log.athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    return render_template("coach/view_log.html", log=log)

