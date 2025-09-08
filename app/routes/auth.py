from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, abort, send_file
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity,JWTManager,get_jwt,set_access_cookies
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash
import io, csv
from app.models.activity_log import ActivityLog


from app import db
from app.models.user import User
from app.schemas.user import UserSchema

auth_bp = Blueprint("auth", __name__)

user_schema = UserSchema()

@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = 'athlete'
    
    status = "pending"

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    new_user = User(email=email, role=role, name=name, status=status)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Registered successfully. Please wait for admin approval."}), 201

@auth_bp.route("/register-pending")
def register_pending():
    return render_template("auth/register-pending.html")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")  


@auth_bp.route("/login", methods=["POST"])
def login_post():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON"}), 400

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401
    
    if user.status == "pending":
        return jsonify({"msg": "Account is pending approval"}), 403
    if user.status == "suspended":
        return jsonify({"msg": "Account is suspended"}), 403    
    if not isinstance(user.id, (int, str)):
        print("Invalid user ID type:", type(user.id))
        return jsonify({"msg": "Internal server error: Invalid user ID"}), 500
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    session["access_token"] = access_token
    session["user_id"] = user.id
    session["role"] = user.role
    response = jsonify({"login": True})
    set_access_cookies(response, access_token)

    return response


@auth_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_with_profile(user_id):
    user = User.query.get_or_404(user_id)

    # بناء الداتا الأساسية
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else None
    }

    # إضافة بيانات البروفايل حسب الدور
    if user.role == "admin" and user.admin_profile:
        user_data["profile"] = {
            "permissions": user.admin_profile.permissions,
            "is_superadmin": user.admin_profile.is_superadmin
        }
    elif user.role == "coach" and user.coach_profile:
        user_data["profile"] = {
            "team": user.coach_profile.team,
            "experience_years": user.coach_profile.experience_years
        }
    elif user.role == "athlete" and user.athlete_profile:
        user_data["profile"] = {
            "sport": user.athlete_profile.sport,
            "position": user.athlete_profile.position
        }
    else:
        user_data["profile"] = None

    return jsonify(user_data), 200



@auth_bp.route("/", methods=["GET"])
@auth_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_users(user_id=None):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # السماح فقط للـ Admin يشوف الكل
    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    if user_id:  # جلب يوزر واحد
        user = User.query.get_or_404(user_id)
        return jsonify(serialize_user_with_profile(user)), 200

    # فلترة
    role = request.args.get("role")  # admin / coach / athlete
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    query = User.query
    if role:
        query = query.filter_by(role=role)
    if search:
        search = f"%{search}%"
        query = query.filter((User.name.ilike(search)) | (User.email.ilike(search)))

    # فرز
    if hasattr(User, sort_by):
        sort_column = getattr(User, sort_by)
        if order.lower() == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)

    # تنفيذ مع pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "users": [serialize_user_with_profile(u) for u in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200


def serialize_user_with_profile(user):
    """تحويل اليوزر ل JSON مع البروفايل"""
    data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else None
    }

    if user.role == "admin" and user.admin_profile:
        data["profile"] = {
            "permissions": user.admin_profile.permissions,
            "is_superadmin": user.admin_profile.is_superadmin
        }
    elif user.role == "coach" and user.coach_profile:
        data["profile"] = {
            "team": getattr(user.coach_profile, "team", None),
            "experience_years": getattr(user.coach_profile, "experience_years", None)
        }
    elif user.role == "athlete" and user.athlete_profile:
        data["profile"] = {
            "sport": getattr(user.athlete_profile, "sport", None),
            "position": getattr(user.athlete_profile, "position", None)
        }
    else:
        data["profile"] = None

    return data


@auth_bp.route("/reset_password/<int:user_id>", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    new_password = data.get("new_password")

    if not new_password or len(new_password) < 6:
        return jsonify({"msg": "Password must be at least 6 characters"}), 400

    user = User.query.get_or_404(user_id)
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    return jsonify({"msg": f"Password for {user.name} reset successfully"}), 200

@auth_bp.route("/export_logs", methods=["GET"])
@jwt_required()
def export_logs():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "User Name", "Action", "Timestamp", "Details"])

    for log in logs:
        writer.writerow([
            log.user_id,
            log.user.name if log.user else "N/A",
            log.action,
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.details or ""
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="activity_logs.csv"
    )


##### logout #####
@auth_bp.route("/logout")
@jwt_required()
def logout():
    session.clear()
    return redirect(url_for("auth.login"))