import os
from flask import Blueprint, request, redirect, url_for, flash,jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models.user import User
from app import db
from app.models import AdminProfile

user_bp = Blueprint("user", __name__)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_FOLDER = "app/static/uploads"

default_image = 'default.jpg'
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@user_bp.route("/profile/image", methods=["POST"])
@jwt_required()
def update_profile_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if "profile_image" not in request.files:
        return jsonify({"msg": "No image provided"}), 400

    file = request.files["profile_image"]
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        if user.profile_image != default_image:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, user.profile_image))
            except Exception:
                pass

        user.profile_image = filename
        db.session.commit()

        return jsonify({"msg": "Image uploaded", "new_image": filename}), 200
    return jsonify({"msg": "Invalid file type"}), 400

@user_bp.route("/profile/image/delete", methods=["POST"])
@jwt_required()
def delete_profile_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if user.profile_image != default_image:
        try:
            os.remove(os.path.join("static/uploads", user.profile_image))
        except Exception:
            pass
        user.profile_image = default_image
        db.session.commit()

    return jsonify({"msg": "Image removed"}), 200

@user_bp.route("/profile")
@jwt_required()
def user_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("users-profile.html", user=user)

@user_bp.route("/image")
@jwt_required()
def image_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("shared/base.html", user=user)


@user_bp.route("/profile", methods=["POST"])
@jwt_required()
def update_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    name = request.form.get("name")
    image_file = request.files.get("profile_image")

    if name:
        user.name = name

    # handle image
    if image_file and image_file.filename != "":
        if allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)

            # ✅ تأكدي إن الفولدر موجود
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)

            image_file.save(image_path)

            # حذف الصورة القديمة لو مش الديفولت
            if user.profile_image and user.profile_image != "default.jpg":
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, user.profile_image))
                except Exception:
                    pass

            user.profile_image = filename

    db.session.commit()
    return jsonify({"msg": "Profile updated", "new_image": user.profile_image}), 200

@user_bp.route("/update-password", methods=["POST"])
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


@user_bp.route("/update/<int:id>", methods=["PUT"])
@jwt_required()
def update_user(id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    # ✅ لو اللي بيعدل غير نفسه → لازم يكون super admin
    if current_user.id != id:
        if not (current_user.admin_profile and current_user.admin_profile.is_superadmin):
            return jsonify({"msg": "Not authorized"}), 403

    user = User.query.get_or_404(id)
    data = request.get_json()

    new_role = data.get("role")
    if new_role and new_role != user.role:
        # reset old relations
        if user.role == "coach":
            for link in user.athlete_links.all():
                db.session.delete(link)

        if user.role == "athlete":
            for group in user.group_assignments.all():
                db.session.delete(group)
            for plan in user.plan_assignments.all():
                db.session.delete(plan)

        user.role = new_role

        # handle super_admin flag
        if new_role == "super_admin":
            if not user.admin_profile:
                user.admin_profile = AdminProfile(user_id=user.id)
            user.admin_profile.is_superadmin = True
            # ✅ super admin ياخد كل الصلاحيات
            user.admin_profile.permissions = ["manage_users", "view_reports", "edit_coaches"]
        else:
            if user.admin_profile:
                user.admin_profile.is_superadmin = False

    # update permissions (لو مش super admin)
    if "permissions" in data and user.role == "admin":
        if not user.admin_profile:
            user.admin_profile = AdminProfile(user_id=user.id)
        user.admin_profile.permissions = data["permissions"]

    db.session.commit()
    return jsonify({"msg": "User updated successfully"}), 200

@user_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_user(id):
    user = User.query.get_or_404(id)

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "permissions": user.admin_profile.permissions if user.admin_profile else []
    })
