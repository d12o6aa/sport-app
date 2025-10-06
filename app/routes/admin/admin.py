from flask import Blueprint, request, jsonify, render_template, url_for, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, AdminProfile
from app.utils.decorators import inject_user_to_template 
from . import admin_bp

# 🆕 دالة مساعدة للتحقق من الصلاحيات
def is_superadmin(user):
    return user and user.admin_profile and user.admin_profile.is_superadmin

def has_permission(user, permission_key):
    if is_superadmin(user):
        return True
    
    if user and user.admin_profile and user.admin_profile.permissions:

        return user.admin_profile.permissions.get(permission_key, False)
    
    return False

@admin_bp.context_processor
def inject_user_permissions():
    user = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            user = User.query.get(user_id)
    except Exception:
        pass
    
    return {'current_user': user}
# =========================================================
# Admin Management Routes
# =========================================================

# 🆕 تعديل دالة إضافة الأدمن
@admin_bp.route("/add_admin", methods=["POST"])
@jwt_required()
def add_admin():
    identity = get_jwt_identity()
    user = User.query.filter_by(id=identity).first()

    # 🆕 فحص الصلاحية: هل يمكن للمستخدم إدارة الأدمنز؟
    if not has_permission(user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not all([name, email, password]):
        return jsonify({"msg": "Missing data"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409

    password_hash = generate_password_hash(password)
    new_user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        status='active',
        role='admin'
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Admin added successfully"}), 200

# 🆕 تعديل دالة إدارة الأدمنز
@admin_bp.route("/manage_admins")
@inject_user_to_template
def manage_admins(current_user): 
    if not current_user.is_admin:
        return "Unauthorized: You don't have permission to view this page.", 403

    # ... (the rest of your logic)
    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    pagination = (
        User.query
        .filter(User.role == "admin", User.id != current_user.id)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    admins = pagination.items
    admin_count = pagination.total
    active_count = User.query.filter_by(role='admin', status='active').count()
    suspended_count = User.query.filter_by(role='admin', status='suspended').count()
    
    return render_template("admin/manage_admins.html",
                            current_user=current_user,
                            admins=admins,
                            admin_count=admin_count,
                            active_count=active_count,
                            suspended_count=suspended_count,
                            pagination=pagination,
                            current_user_is_superadmin=is_superadmin(current_user))

# 🆕 تعديل دالة تعديل الأدمن
@admin_bp.route("/edit_admin/<int:id>", methods=["GET", "POST"])
@jwt_required()
def edit_admin(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    # 🆕 فحص الصلاحية: فقط السوبر أدمن يمكنه تعديل الأدمنز
    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can edit other admins"}), 403

    admin = User.query.get_or_404(id)

    if request.method == "POST":
        data = request.get_json()
        admin.name = data.get("name", admin.name)
        admin.email = data.get("email", admin.email)
        db.session.commit()
        return jsonify({"msg": "Admin updated successfully"}), 200

    return jsonify({
        "id": admin.id,
        "name": admin.name,
        "email": admin.email
    }), 200

# 🆕 تعديل دالة حذف الأدمن
@admin_bp.route("/delete_admin/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_admin(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    # 🆕 فحص الصلاحية: فقط السوبر أدمن يمكنه حذف الأدمنز
    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can delete admins"}), 403

    admin = User.query.get_or_404(id)
    db.session.delete(admin)
    db.session.commit()
    return jsonify({"msg": "Admin deleted successfully"}), 200

# 🆕 تعديل دالة تفعيل/تعطيل الأدمن
@admin_bp.route("/toggle_active/<int:id>", methods=["PATCH"])
@jwt_required()
def toggle_active(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    # 🆕 فحص الصلاحية: هل يمكن للمستخدم إدارة الأدمنز؟
    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    admin = User.query.get_or_404(id)
    if admin.status == 'active':
        admin.status = 'suspended'
    else:
        admin.status = 'active'
    db.session.commit()

    return jsonify({
        "msg": f"Admin {'activated' if admin.status == 'active' else 'deactivated'} successfully",
        "status": admin.status
    }), 200

# 🆕 تعديل دالة التعديل الشامل
@admin_bp.route("/update_admin/<int:id>", methods=["PUT"])
@jwt_required()
def update_admin(id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # 🆕 فحص الصلاحية: فقط السوبر أدمن يمكنه تعديل الأدمنز
    if not is_superadmin(current_user):
        return jsonify({"msg": "Only super admin can update admins"}), 403

    data = request.get_json()
    user = User.query.get_or_404(id)
    return update_user_logic(user, data)


# 🆕 تعديل دالة جلب بيانات الأدمن (لصلاحيات التعديل)
@admin_bp.route("/get_admin/<int:id>", methods=["GET"])
@jwt_required()
def get_admin(id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # You must have permission to get admin data
    if not is_superadmin(current_user): # Or has_permission(current_user, "can_manage_admins")
        return jsonify({"msg": "Unauthorized"}), 403

    admin = User.query.filter_by(id=id, role="admin").first()
    if not admin:
        return jsonify({"msg": "Admin not found"}), 404
        
    admin_profile = AdminProfile.query.filter_by(user_id=id).first()
    
    # Check if the profile exists before accessing permissions
    permissions = admin_profile.permissions if admin_profile else {}
    is_super = admin_profile.is_superadmin if admin_profile else False

    return jsonify({
        "name": admin.name,
        "email": admin.email,
        "is_superadmin": is_super,
        "permissions": permissions,
        "role": admin.role
    })



# 🆕 تعديل دوال المهام الجماعية (Bulk Actions)
@admin_bp.route("/bulk_delete", methods=["POST"])
@jwt_required()
def bulk_delete():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # 🆕 فحص الصلاحية: هل يمكن للمستخدم إدارة الأدمنز؟
    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403
    
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"msg": "No user IDs provided"}), 400
    ids = [uid for uid in ids if uid != current_user.id]
    User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"msg": "Users deleted successfully"}), 200

@admin_bp.route("/bulk_change_role", methods=["POST"])
@jwt_required()
def bulk_change_role():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # 🆕 فحص الصلاحية: هل يمكن للمستخدم إدارة الأدمنز؟
    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    data = request.get_json()
    ids = data.get("ids", [])
    new_role = data.get("role")
    if not ids or not new_role:
        return jsonify({"msg": "IDs and new role are required"}), 400
    ids = [uid for uid in ids if uid != current_user.id]
    User.query.filter(User.id.in_(ids)).update({"role": new_role}, synchronize_session=False)
    db.session.commit()
    return jsonify({"msg": f"Users updated to {new_role} successfully"}), 200


@admin_bp.route("/reset_password/<int:user_id>", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # 🆕 فحص الصلاحية: هل يمكن للمستخدم إدارة الأدمنز؟
    if not has_permission(current_user, "can_manage_admins"):
        return jsonify({"msg": "Unauthorized: Cannot manage admins"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404
    new_password = "Default@123"
    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": f"Password reset to {new_password}"}), 200



# =========================================================
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
    unassigned = User.query.filter_by(status='suspended').count()

    return render_template(
        'admin/user_management.html',
        total_users=total_users,
        admins=admins,
        coaches=coaches,
        athletes=athletes,
        unassigned=unassigned
    )


def update_user_logic(user, data):
    """لوجيك موحّد لتحديث أي يوزر"""
    new_role = data.get("role")

    if new_role and new_role != user.role:
        # Reset old relations
        if user.role == "coach":
            for link in user.athlete_links.all():
                db.session.delete(link)

        if user.role == "athlete":
            for group in user.group_assignments.all():
                db.session.delete(group)
            for plan in user.plan_assignments.all():
                db.session.delete(plan)

        # ✅ Update role (admin / coach / athlete)
        if new_role in ["admin", "coach", "athlete"]:
            user.role = new_role

    # ✅ Handle super_admin flag
    if "is_superadmin" in data and user.role == "admin":
        if not user.admin_profile:
            user.admin_profile = AdminProfile(user_id=user.id)
        user.admin_profile.is_superadmin = bool(data["is_superadmin"])

    # ✅ Update permissions
    if "permissions" in data:
        if not user.admin_profile:
            user.admin_profile = AdminProfile(user_id=user.id)
        user.admin_profile.permissions = data["permissions"]

    db.session.commit()
    return jsonify({"msg": "User updated successfully"}), 200


@admin_bp.route("/some-protected-route")
@jwt_required()
def protected_area():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    # check permission properly
    if not user.admin_profile or not user.admin_profile.permissions.get("can_manage_users", False):
        return "Unauthorized", 403

    return jsonify({"msg": "Welcome, authorized user!"}), 200


@admin_bp.route("/change_role/<int:user_id>", methods=["POST"])
@jwt_required()
def change_role(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or current_user.role != "admin" or not current_user.admin_profile or not current_user.admin_profile.is_superadmin:
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    new_role = data.get("role")

    if new_role not in ["admin", "coach", "athlete"]:
        return jsonify({"msg": "Invalid role"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    old_role = user.role
    user.role = new_role
    db.session.commit()

    return jsonify({"msg": f"Role changed from {old_role} to {new_role} successfully"}), 200

@admin_bp.route("/profile")
@jwt_required()
def user_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("users-profile.html", user=user)

@admin_bp.route("/image")
@jwt_required()
def image_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("shared/base.html", user=user)

@admin_bp.route("/profile", methods=["POST"])
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    user.name = data.get("name")
    db.session.commit()
    return redirect(url_for("admin.user_profile"))

@admin_bp.route("/update-password", methods=["POST"])
@jwt_required()
def update_password():
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

