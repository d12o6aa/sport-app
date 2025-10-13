from flask import Blueprint, jsonify, render_template, request, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc, or_
from datetime import datetime
from app import db
from app.models import (
    User, CoachAthlete, WorkoutLog,
    ReadinessScore, TrainingPlan, AthleteProfile
)

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def coach_dashboard():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        linked_athletes = CoachAthlete.query.filter_by(coach_id=identity).all()
        athlete_ids = [link.athlete_id for link in linked_athletes]

        # Calculate overall team stats
        total_athletes_count = len(athlete_ids)
        active_athletes_count = CoachAthlete.query.filter_by(coach_id=identity, is_active=True).count()
        
        avg_readiness_data = db.session.query(func.avg(ReadinessScore.score)).filter(
            ReadinessScore.athlete_id.in_(athlete_ids)
        ).scalar()
        avg_readiness = round(avg_readiness_data, 1) if avg_readiness_data is not None else "N/A"
        
        # New overall stats
        total_workouts_count = db.session.query(func.count(WorkoutLog.id)).filter(
            WorkoutLog.athlete_id.in_(athlete_ids)
        ).scalar() or 0
        total_plans_count = db.session.query(func.count(TrainingPlan.id)).filter(
            TrainingPlan.coach_id == identity
        ).scalar() or 0

        # Find athletes at high risk (low readiness or high injury risk)
        high_risk_athletes_query = db.session.query(User).join(ReadinessScore, ReadinessScore.athlete_id == User.id).filter(
            ReadinessScore.athlete_id.in_(athlete_ids),
            or_(
                ReadinessScore.score < 50,
                ReadinessScore.injury_risk == 'High'
            )
        )
        high_risk_athletes = high_risk_athletes_query.all()
        
        high_risk_details = []
        for athlete in high_risk_athletes:
            readiness_data = ReadinessScore.query.filter_by(athlete_id=athlete.id).order_by(desc(ReadinessScore.date)).first()
            if readiness_data:
                high_risk_details.append({
                    "id": athlete.id,
                    "name": athlete.name,
                    "readiness_score": readiness_data.score,
                    "injury_risk": readiness_data.injury_risk,
                })
            
        subquery = db.session.query(WorkoutLog.athlete_id).group_by(WorkoutLog.athlete_id).subquery()
        no_data_athletes_query = db.session.query(User).filter(
            User.id.in_(athlete_ids),
            ~User.id.in_(subquery)
        )
        no_data_athletes = no_data_athletes_query.all()
        
        no_data_details = [{
            "id": athlete.id,
            "name": athlete.name,
            "readiness_score": "No Data",
            "injury_risk": "No Data",
        } for athlete in no_data_athletes]

        attention_needed_athletes = high_risk_details + no_data_details
        
        return render_template(
            "dashboard/coach_dashboard.html",
            total_athletes=total_athletes_count,
            active_athletes=active_athletes_count,
            avg_readiness=avg_readiness,
            total_workouts=total_workouts_count,
            total_plans=total_plans_count,
            attention_needed_athletes=attention_needed_athletes,
        )

    except Exception as e:
        print(f"FATAL ERROR in coach_dashboard: {e}")
        return jsonify({"msg": "An error occurred while loading dashboard data."}), 500