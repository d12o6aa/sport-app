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
from app.models.activity_log import ActivityLog
from app.schemas.user import UserSchema

auth_bp = Blueprint("auth", __name__)
user_schema = UserSchema()

# Rate limiter - يجب إضافة هذا في __init__.py
# limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

def validate_password(password):
    """التحقق من قوة كلمة المرور"""
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

def log_activity(user_id, action, details=None):
    """تسجيل النشاطات الأمنية"""
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Failed to log activity: {e}")

@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("auth/register.html")

@auth_bp.route("/register", methods=["POST"])
# @limiter.limit("5 per hour")  # تفعيل بعد إضافة limiter
def register():
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    # التحقق من البيانات
    if not name or not email or not password:
        return jsonify({"msg": "All fields are required"}), 400
    
    if len(name) < 2:
        return jsonify({"msg": "Name must be at least 2 characters"}), 400
    
    # التحقق من صحة الإيميل
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({"msg": "Invalid email format"}), 400
    
    # التحقق من قوة كلمة المرور
    is_valid, msg = validate_password(password)
    if not is_valid:
        return jsonify({"msg": msg}), 400

    # التحقق من وجود الإيميل
    if User.query.filter_by(email=email).first():
        log_activity(None, "failed_registration", f"Email already exists: {email}")
        return jsonify({"msg": "Registration failed"}), 400

    # إنشاء المستخدم
    new_user = User(
        email=email, 
        role='athlete', 
        name=name, 
        status="pending"
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()
    
    log_activity(new_user.id, "user_registered", f"New user: {email}")

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
# @limiter.limit("10 per 15 minutes")  # تفعيل بعد إضافة limiter
def login_post():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON"}), 400

    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    
    # استخدام رسالة عامة لعدم الكشف عن معلومات
    if not user or not user.check_password(password):
        log_activity(None, "failed_login", f"Failed login attempt for: {email}")
        return jsonify({"msg": "Invalid credentials"}), 401
    
    # التحقق من حالة الحساب
    if user.status == "pending":
        log_activity(user.id, "login_attempt_pending", "Pending account tried to login")
        return jsonify({"msg": "Account is pending approval"}), 403
    
    if user.status == "suspended":
        log_activity(user.id, "login_attempt_suspended", "Suspended account tried to login")
        return jsonify({"msg": "Account is suspended"}), 403

    # إنشاء التوكن مع مدة صلاحية
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
        expires_delta=timedelta(hours=24)
    )
    
    log_activity(user.id, "user_login", f"Successful login from IP: {request.remote_addr}")
    
    # استخدام httpOnly cookies فقط
    response = jsonify({
        "msg": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role
        }
    })
    
    # تعيين الكوكيز بشكل آمن
    set_access_cookies(response, access_token)
    
    return response, 200

@auth_bp.route("/<int:user_id>", methods=["GET"])
@jwt_required()
def get_user_with_profile(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)
    
    if not current_user:
        return jsonify({"msg": "Unauthorized"}), 401
    
    # التحقق من الصلاحيات
    if current_user.role != "admin" and str(current_user.id) != str(user_id):
        log_activity(current_user.id, "unauthorized_access_attempt", 
                    f"Tried to access user {user_id}")
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
@jwt_required()
def get_users():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    # الفلترة
    role = request.args.get("role")
    search = request.args.get("search", "").strip()
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 10)), 100)  # حد أقصى 100

    query = User.query
    
    if role and role in ["admin", "coach", "athlete"]:
        query = query.filter_by(role=role)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.name.ilike(search_pattern)) | 
            (User.email.ilike(search_pattern))
        )

    # الفرز الآمن
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
    """تحويل المستخدم إلى JSON مع البروفايل"""
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
    new_password = data.get("new_password", "")

    # التحقق من قوة كلمة المرور
    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return jsonify({"msg": msg}), 400

    user = User.query.get_or_404(user_id)
    user.set_password(new_password)
    db.session.commit()
    
    log_activity(current_user.id, "password_reset", 
                f"Admin reset password for user: {user.email}")

    return jsonify({"msg": f"Password reset successfully"}), 200

@auth_bp.route("/export_logs", methods=["GET"])
@jwt_required()
def export_logs():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10000).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "User Name", "Action", "Timestamp", "Details"])

    for log in logs:
        writer.writerow([
            log.user_id or "N/A",
            log.user.name if log.user else "System",
            log.action,
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.details or ""
        ])

    output.seek(0)
    
    log_activity(current_user.id, "logs_exported", "Activity logs exported")

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"activity_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    identity = get_jwt_identity()
    log_activity(identity, "user_logout", "User logged out")
    
    response = jsonify({"msg": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200