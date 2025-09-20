from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import LoginLog, Complaint
from app.models import AdminProfile, User
from datetime import datetime

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/support_security", methods=["GET"])
@jwt_required()
def support_security():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    login_logs = LoginLog.query.order_by(LoginLog.created_at.desc()).all()
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template("admin/support_security.html", login_logs=login_logs, complaints=complaints)