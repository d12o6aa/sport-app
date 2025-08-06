import os
from flask import Blueprint, request, redirect, url_for, flash,jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models.user import User
from app import db

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
