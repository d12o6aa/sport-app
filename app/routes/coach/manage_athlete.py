# manage_athlete.py

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, TrainingPlan, WorkoutLog, Feedback, Message, ActivityLog, AthleteProgress, HealthRecord, ReadinessScore, InjuryRecord, AthleteProfile, AthletePlan
from werkzeug.security import generate_password_hash

from . import coach_bp

# Helper function to check if user is a coach
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# Get athletes assigned to the coach
@coach_bp.route("/athletes", methods=["GET"])
@jwt_required()
def get_coach_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User, AthleteProfile, func.max(ActivityLog.created_at), func.count(WorkoutLog.id), func.count(WorkoutLog.id).filter(WorkoutLog.compliance_status == "completed"))
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .outerjoin(AthleteProfile, AthleteProfile.user_id == User.id)
        .outerjoin(ActivityLog, ActivityLog.user_id == User.id)
        .outerjoin(WorkoutLog, WorkoutLog.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .group_by(User, AthleteProfile)
        .all()
    )

    return jsonify([
        {
            "id": a.User.id,
            "name": a.User.name,
            "email": a.User.email,
            "status": a.User.status,
            "last_activity": a[2].strftime("%Y-%m-%d %H:%M") if a[2] else "N/A",
            "compliance": round((a[4] / a[3] * 100) if a[3] > 0 else 0, 1)
        }
        for a in athletes
    ])

# Get athlete details
@coach_bp.route("/athlete/<int:athlete_id>", methods=["GET"])
@jwt_required()
def get_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()

    return jsonify({
        "id": athlete.id,
        "name": athlete.name,
        "email": athlete.email,
        "age": profile.age if profile else None,
        "gender": profile.gender if profile else None,
        "weight": profile.weight if profile else None,
        "height": profile.height if profile else None
    })

# Add new athlete
@coach_bp.route("/athlete/add", methods=["POST"])
@jwt_required()
def add_athlete():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    age = data.get("age")
    gender = data.get("gender")
    weight = data.get("weight")
    height = data.get("height")

    if not name or not email or not password:
        return jsonify({"msg": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already registered"}), 400

    try:
        new_athlete = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            role="athlete",
            status="active"
        )
        db.session.add(new_athlete)
        db.session.flush()

        profile = AthleteProfile(
            user_id=new_athlete.id,
            age=age,
            gender=gender,
            weight=weight,
            height=height
        )
        db.session.add(profile)

        link = CoachAthlete(
            coach_id=identity,
            athlete_id=new_athlete.id,
            assigned_at=datetime.utcnow(),
            status="approved",
            is_active=True
        )
        db.session.add(link)

        db.session.commit()
        return jsonify({"msg": "Athlete added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Update athlete
@coach_bp.route("/athlete/<int:athlete_id>", methods=["PUT"])
@jwt_required()
def update_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.get_json()
    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()

    try:
        athlete.name = data.get("name", athlete.name)
        athlete.email = data.get("email", athlete.email)

        if not profile and (data.get("age") or data.get("gender") or data.get("weight") or data.get("height")):
            profile = AthleteProfile(user_id=athlete_id)
            db.session.add(profile)

        if profile:
            profile.age = data.get("age", profile.age)
            profile.gender = data.get("gender", profile.gender)
            profile.weight = data.get("weight", profile.weight)
            profile.height = data.get("height", profile.height)

        db.session.commit()
        return jsonify({"msg": "Athlete updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Remove athlete
@coach_bp.route("/athlete/<int:athlete_id>", methods=["DELETE"])
@jwt_required()
def delete_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    link.is_active = False
    db.session.commit()
    return jsonify({"msg": "Athlete removed successfully"}), 200

# Manage athletes
@coach_bp.route("/manage_athletes", methods=["GET"])
@jwt_required()
def manage_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    return render_template("coach/manage_athletes.html")
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    return render_template("coach/manage_athletes.html")