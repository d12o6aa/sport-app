from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import Equipment, Event, WorkoutType, User ,TrainingPlan  # Added WorkoutType model

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/gym_management", methods=["GET"])
@jwt_required()
def gym_management():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    equipments = Equipment.query.all()
    events = Event.query.all()
    workout_types = WorkoutType.query.all()
    return render_template("admin/gym_management.html", equipments=equipments, events=events, workout_types=workout_types)

@admin_bp.route("/add_equipment", methods=["POST"])
@jwt_required()
def add_equipment():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.form
    equipment = Equipment(
        name=data.get("name"),
        description=data.get("description"),
        status=data.get("status", "available"),
        created_at=datetime.utcnow()
    )
    db.session.add(equipment)
    db.session.commit()
    flash("Equipment added successfully!", "success")
    return redirect(url_for("gym_management.gym_management"))

@admin_bp.route("/add_event", methods=["POST"])
@jwt_required()
def add_event():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.form
    event = Event(
        title=data.get("title"),
        description=data.get("description"),
        date=datetime.strptime(data.get("date"), "%Y-%m-%d"),
        created_at=datetime.utcnow()
    )
    db.session.add(event)
    db.session.commit()
    flash("Event added successfully!", "success")
    return redirect(url_for("gym_management.gym_management"))

@admin_bp.route("/add_workout_type", methods=["POST"])
@jwt_required()
def add_workout_type():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.form
    workout_type = WorkoutType(
        name=data.get("name"),
        description=data.get("description")
    )
    db.session.add(workout_type)
    db.session.commit()
    flash("Workout type added successfully!", "success")
    return redirect(url_for("gym_management.gym_management"))

@admin_bp.route("/add_workout_plan", methods=["POST"])
@jwt_required()
def add_workout_plan():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.form
    workout_plan = TrainingPlan(
        title=data.get("title"),
        description=data.get("description"),
        workout_type_id=data.get("workout_type_id"),
        exercises=[{"name": ex["name"], "sets": ex["sets"], "reps": ex["reps"]} for ex in request.json.get("exercises", [])]
    )
    db.session.add(workout_plan)
    db.session.commit()
    flash("Workout plan added successfully!", "success")
    return redirect(url_for("gym_management.gym_management"))