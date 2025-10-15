from flask import Blueprint, request, jsonify, redirect, url_for, render_template, abort, send_file
from flask_jwt_extended import (
    create_access_token, 
    jwt_required, 
    get_jwt_identity,
    set_access_cookies,
    unset_jwt_cookies
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash
import io
import csv
import re
from datetime import datetime, timedelta

from app import db
from app.models.user import User
from app.schemas.user import UserSchema

auth_bp = Blueprint("auth", __name__)
user_schema = UserSchema()
DEFAULT_PASSWORD = "Default@1234"

def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

# The log_activity function has been removed.

@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")

@auth_bp.route("/register", methods=["POST"])
# @limiter.limit("5 per hour")
def register():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not name or not email or not password:
        return jsonify({"msg": "All fields are required"}), 400
    
    if len(name) < 2:
        return jsonify({"msg": "Name must be at least 2 characters"}), 400
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({"msg": "Invalid email format"}), 400
    
    is_valid, msg = validate_password(password)
    if not is_valid:
        return jsonify({"msg": msg}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Registration failed"}), 400

    new_user = User(
        email=email, 
        role='athlete', 
        name=name, 
        status="pending"
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "msg": "Registered successfully. Please wait for admin approval."
    }), 201

@auth_bp.route("/register-pending")
def register_pending():
    return render_template("auth/register-pending.html")

@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("auth/login.html")

@auth_bp.route("/login", methods=["POST"])
# @limiter.limit("10 per 15 minutes")
def login_post():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON"}), 400

    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    
    # if not user or not user.check_password(password):
    #     return jsonify({"msg": "Invalid credentials"}), 401
    if not user:
        print(f"Login failed: User with email {email} not found.")
        return jsonify({"msg": "Invalid credentials"}), 401

    if user.check_password(password):
        print(f"Login successful for user {user.email}")
    else:
        print(f"Login failed: Incorrect password for user {user.email}")
        return jsonify({"msg": "Invalid credentials"}), 401


    if user.status == "pending":
        return jsonify({"msg": "Account is pending approval"}), 403
    
    if user.status == "suspended":
        return jsonify({"msg": "Account is suspended"}), 403

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
        expires_delta=timedelta(hours=24)
    )
    
    response = jsonify({
        "msg": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role
        }
    })
    
    set_access_cookies(response, access_token)
    
    return response, 200

@auth_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_with_profile(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)
    
    if not current_user:
        return jsonify({"msg": "Unauthorized"}), 401
    
    if not (current_user.role == "admin" or str(current_user.id) == str(user_id)):
        return jsonify({"msg": "Unauthorized"}), 403
    
    user = User.query.get_or_404(user_id)
    
    user_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "created_at": user.created_at.strftime("%Y-%m-%d") if user.created_at else None
    }

    if user.role == "admin" and user.admin_profile:
        user_data["profile"] = {
            "permissions": user.admin_profile.permissions,
            "is_superadmin": user.admin_profile.is_superadmin
        }
    elif user.role == "coach" and user.coach_profile:
        user_data["profile"] = {
            "team": getattr(user.coach_profile, "team", None),
            "experience_years": getattr(user.coach_profile, "experience_years", None)
        }
    elif user.role == "athlete" and user.athlete_profile:
        user_data["profile"] = {
            "sport": getattr(user.athlete_profile, "sport", None),
            "position": getattr(user.athlete_profile, "position", None)
        }
    else:
        user_data["profile"] = None

    return jsonify(user_data), 200

@auth_bp.route("/", methods=["GET"])
@jwt_required()
def get_users():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    role = request.args.get("role")
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 10)), 100)

    query = User.query
    
    if role and role in ["admin", "coach", "athlete"]:
        query = query.filter_by(role=role)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern))
        )

    allowed_sort_fields = ["created_at", "name", "email", "role", "status"]
    if sort_by in allowed_sort_fields:
        sort_column = getattr(User, sort_by)
        if order.lower() == "desc":
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "users": [serialize_user_with_profile(u) for u in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200

def serialize_user_with_profile(user):
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
# auth/reset_password/<int:user_id>
@auth_bp.route("/reset_password/<int:user_id>", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    new_password = DEFAULT_PASSWORD

    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return jsonify({"msg": msg}), 400

    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({"msg": f"Password reset successfully"}), 200

@auth_bp.route("/export_logs", methods=["GET"])
@jwt_required()
def export_logs():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "User Name", "Action", "Timestamp", "Details"])

    for log in logs:
        writer.writerow([
            log.user_id or "N/A",
            log.user.name if log.user else "System",
            log.action,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            log.details or ""
        ])

    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"activity_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200