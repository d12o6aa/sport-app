from flask import Blueprint, jsonify, request, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, HealthRecord,athlete_profile
from app.extensions import db
from werkzeug.utils import secure_filename
import os
from . import athlete_bp



@athlete_bp.route("/api/profile/upload", methods=["POST"])
@jwt_required()
def upload_profile_image():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    filename = secure_filename(file.filename)
    filepath = os.path.join("static/uploads", filename)
    file.save(filepath)

    user.profile_image = f"/static/uploads/{filename}"
    db.session.commit()
    return jsonify({"msg": "Image updated", "image_url": user.profile_image})
