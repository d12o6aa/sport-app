from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app import db
from app.models import User, Subscription, WorkoutLog

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    num_members = User.query.count()
    attendance_rate = db.session.query(func.avg(WorkoutLog.attendance_rate)).scalar() or 0  # Assume added field
    return render_template("admin/dashboard.html", num_members=num_members, attendance_rate=attendance_rate)