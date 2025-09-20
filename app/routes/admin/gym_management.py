from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import Equipment, Event,User  # Assume these models
from app.models import Subscription, User
from datetime import datetime


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
    return render_template("admin/gym_management.html", equipments=equipments, events=events)

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
    return redirect(url_for("admin.gym_management"))

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
    return redirect(url_for("admin.gym_management"))