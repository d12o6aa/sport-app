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


coach_bp = Blueprint('coach', __name__)



######### Coach Management Routes #########
@coach_bp.route("/manage_coachs")
@jwt_required()
def manage_coachs():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return "Unauthorized", 403

    coaches = User.query.filter_by(role="coach").all()
    coach_count = User.query.filter_by(role='coach').count()
    active_count = User.query.filter_by(role='coach', is_active=True).count()
    suspended_count = User.query.filter_by(role='coach', is_active=False).count()
    return render_template("admin/manage_coachs.html",
                           coaches=coaches,
                           coach_count=coach_count,
                           active_count=active_count,
                           suspended_count=suspended_count)

@coach_bp.route("/add", methods=["POST"])
@jwt_required()
def add_coach():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user or current_user.role != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            return jsonify({"msg": "Missing fields"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "Email already registered"}), 400

        new_coach = User(
            name=name,
            email=email,
            role="coach",
            is_active=True,
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_coach)
        db.session.commit()

        return jsonify({"msg": "Coach added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Server error: {str(e)}"}), 500
    

@coach_bp.route("/edit_coach/<int:id>", methods=["GET", "POST"])
@jwt_required()
def edit_coach(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)

    if request.method == "POST":
        data = request.get_json()
        coach.name = data.get("name", coach.name)
        coach.email = data.get("email", coach.email)
        db.session.commit()
        return jsonify({"msg": "Coach updated successfully"}), 200

    return jsonify({
        "id": coach.id,
        "name": coach.name,
        "email": coach.email
    }), 200


@coach_bp.route("/delete_coach/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_coach(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)

    db.session.delete(coach)
    db.session.commit()

    return jsonify({"msg": "Coach deleted successfully"}), 200

@coach_bp.route("/toggle_coach_active/<int:id>", methods=["PATCH"])
@jwt_required()
def toggle_coach_active(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)
    coach.is_active = not coach.is_active
    db.session.commit()

    return jsonify({
        "msg": f"Coach {'activated' if coach.is_active else 'deactivated'} successfully",
        "is_active": coach.is_active
    }), 200

@coach_bp.route("/view_athletes/<int:coachId>", methods=["GET"])
@jwt_required()
def view_athletes(coachId):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        # التأكد إن المستخدم admin
        if not current_user or current_user.role != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        # جلب المدرب
        coach = User.query.get(coachId)
        if not coach:
            return jsonify({"msg": "Coach not found"}), 404

        # جلب الرياضيين المرتبطين بالمدرب
        # هنفترض إن في علاقة في موديل User اسمها athletes
        athletes = [
            {"id": athlete.id, "name": athlete.name, "email": athlete.email}
            for athlete in coach.athletes
        ]

        return jsonify({"athletes": athletes}), 200
    except Exception as e:
        return jsonify({"msg": f"Server error: {str(e)}"}), 500


@coach_bp.route("/update_coach/<int:id>", methods=["PUT"])
@jwt_required()
def update_coach(id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or not user.is_superadmin:
        return jsonify({"msg": "Only super admin can update coaches"}), 403

    data = request.get_json()

    coach = User.query.filter_by(id=id, role="coach").first()
    if not coach:
        return jsonify({"msg": "Coach not found"}), 404

    coach.permissions = data.get("permissions", coach.permissions)

    db.session.commit()
    return jsonify({"msg": "Coach updated successfully"}), 200

@coach_bp.route("/get_coach/<int:id>")
@jwt_required()
def get_coach(id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or not user.is_superadmin:
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.filter_by(id=id, role="coach").first()
    if not coach:
        return jsonify({"msg": "Coach not found"}), 404

    return jsonify({
        "permissions": coach.permissions,
    })

@coach_bp.route("/some-coach-protected-route")
@jwt_required()
def coach_protected_area():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if "manage_users" not in user.permissions:
        return "Unauthorized", 403

    # allowed logic here


@coach_bp.route("/coach_profile")
@jwt_required()
def coach_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("coaches-profile.html", user=user)

@coach_bp.route("/coach_image")
@jwt_required()
def coach_image_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("shared/base.html", user=user)

@coach_bp.route("/coach_profile", methods=["POST"])
@jwt_required()
def update_coach_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    user.name = data.get("name")
    db.session.commit()
    return redirect(url_for("admin.coach_profile"))

@coach_bp.route("/coach_update-password", methods=["POST"])
@jwt_required()
def update_coach_password():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not user.check_password(current_password):
        return jsonify({"msg": "Wrong current password"}), 400

    if new_password != confirm_password:
        return jsonify({"msg": "Passwords do not match"}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": "Password updated successfully"}), 200

@coach_bp.route("/admin_dashboard")
@jwt_required()
def admin_dashboard():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or user.role.lower() != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    total_users = User.query.count()
    admins = User.query.filter_by(role='admin').count()
    coaches = User.query.filter_by(role='coach').count()
    athletes = User.query.filter_by(role='athlete').count()

    return render_template(
        'admin/admin_dashboard.html',
        total_users=total_users,
        admins=admins,
        coaches=coaches,
        athletes=athletes
    )