from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash

from flask_jwt_extended import JWTManager
from flask import current_app

from app import db
from app.models.user import User
from app.schemas.user import UserSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask import render_template


admin_bp = Blueprint('admin', __name__)


@admin_bp.route("/add_admin", methods=["GET"])
def add_admin_page():
    return render_template("manage_admins.html")
   
@admin_bp.route("/add_admin", methods=["POST"])
@jwt_required()
def add_admin():
    print("Request headers:", request.headers)
    if request.method == "POST":
        identity = get_jwt_identity()
        print("JWT identity:", identity, "Type:", type(identity))
        user = User.query.filter_by(id=identity).first()

        if not user or user.role.lower() != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = 'admin'

        if not all([name, email, password, role]):
            return jsonify({"msg": "Missing data"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "Email already exists"}), 409

        password_hash = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"msg": "User added successfully"}), 200
    return jsonify({"msg": "Use POST to add user"}), 405

@admin_bp.route("/add_user", methods=["GET"])
def add_user_page():
    return render_template("add_user.html")
   
@admin_bp.route("/add_user", methods=["POST"])
@jwt_required()
def add_user():
    print("Request headers:", request.headers)
    if request.method == "POST":
        identity = get_jwt_identity()
        print("JWT identity:", identity, "Type:", type(identity))
        user = User.query.filter_by(id=identity).first()

        if not user or user.role.lower() != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")

        if not all([name, email, password, role]):
            return jsonify({"msg": "Missing data"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "Email already exists"}), 409

        password_hash = generate_password_hash(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            role=role
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"msg": "User added successfully", "redirect_url": url_for('main_bp.home')}), 200
    return jsonify({"msg": "Use POST to add user"}), 405


@admin_bp.route('/unassigned_athletes', methods=['GET'])
@jwt_required()
def get_unassigned_athletes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can view unassigned athletes"}), 403

    athletes = User.query.filter_by(role='athlete', coach_id=None).all()
    result = [{"id": a.id, "email": a.email} for a in athletes]
    return jsonify(result)


@admin_bp.route('/assign_athlete', methods=['POST'])
@jwt_required()
def assign_athlete():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can assign athletes"}), 403

    data = request.get_json()
    athlete = User.query.get(data['athlete_id'])
    coach = User.query.get(data['coach_id'])

    if not athlete or athlete.role != 'athlete':
        return jsonify({"msg": "Invalid athlete"}), 400
    if not coach or coach.role != 'coach':
        return jsonify({"msg": "Invalid coach"}), 400

    athlete.coach_id = coach.id
    db.session.commit()
    return jsonify({"msg": "Athlete assigned to coach"}), 200



@admin_bp.route('/user_management')
@jwt_required()
def user_management():
    total_users = User.query.count()
    admins = User.query.filter_by(role='admin').count()
    coaches = User.query.filter_by(role='coach').count()
    athletes = User.query.filter_by(role='athlete').count()
    unassigned = User.query.filter_by(is_active=False).count()

    return render_template(
        'admin/user_management.html',
        total_users=total_users,
        admins=admins,
        coaches=coaches,
        athletes=athletes,
        unassigned=unassigned
    )

@admin_bp.route('/admin_views')
@jwt_required()
def admin_views():
    admin_count = User.query.filter_by(role='admin').count()
    active_count = User.query.filter_by(role='admin', is_active=True).count()
    suspended_count = User.query.filter_by(role='admin', is_active=False).count()
    print("Admin:", admin_count)
    print("Active:", active_count)
    print("Suspended:", suspended_count)

    return render_template(
        'admin/manage_admins.html',
        admin_count=admin_count,
        active_count=active_count,
        suspended_count=suspended_count
    )



@admin_bp.route("/manage_admins")
@jwt_required()
def manage_admins():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return "Unauthorized", 403

    admins = User.query.filter_by(role="admin").all()
    return render_template("admin/manage_admins.html", admins=admins)
