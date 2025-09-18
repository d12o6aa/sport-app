from flask import Blueprint, jsonify, request, render_template

from app.models.user import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import render_template, abort, jsonify
from app.models.health_record import HealthRecord
from app.models.athlete_profile import AthleteProfile
from app.models.settings import UserSettings
from . import athlete_bp
from app.extensions import db
from werkzeug.utils import secure_filename
import os
UPLOAD_FOLDER = "app/static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@athlete_bp.route('/unassigned_athletes', methods=['GET'])
@jwt_required()
def get_unassigned_athletes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can view unassigned athletes"}), 403

    athletes = User.query.filter_by(role='athlete', coach_id=None).all()
    result = [{"id": a.id, "email": a.email} for a in athletes]
    return jsonify(result)

@athlete_bp.route("/profile")
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != "athlete":
        return abort(403)
    # آخر health record (لو متاح)
    hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
    profile = AthleteProfile.query.filter_by(user_id=user_id).first()
    
    return render_template("athlete/profile.html", user=user,hr = hr,
        profile= profile,)



# Dashboard
@athlete_bp.route("/dashboard")
@jwt_required()
def dashboard_view():
    return render_template("athlete/dashboard.html")

# Training
@athlete_bp.route("/my_plans")
@jwt_required()
def my_plans():
    return render_template("athlete/my_plans.html")

@athlete_bp.route("/goals")
@jwt_required()
def goals():
    return render_template("athlete/goals.html")

@athlete_bp.route("/my_calendar")
@jwt_required()
def my_calendar():
    return render_template("athlete/schedule.html")  # نربطه بملف schedule.html

# Performance
@athlete_bp.route("/my_stats")
@jwt_required()
def my_stats():
    return render_template("athlete/progress.html")  # نربطه بملف progress.html

@athlete_bp.route("/workout_history")
@jwt_required()
def workout_history():
    return render_template("athlete/workout_history.html")

# Feedback
@athlete_bp.route("/send_feedback")
@jwt_required()
def send_feedback():
    return render_template("athlete/send_feedback.html")

@athlete_bp.route("/view_coach_feedback")
@jwt_required()
def view_coach_feedback():
    return render_template("athlete/view_coach_feedback.html")


@athlete_bp.route("/workouts")
@jwt_required()
def workouts():
    return render_template("athlete/workouts.html")

@athlete_bp.route("/health")
@jwt_required()
def health():
    return render_template("athlete/health.html")


@athlete_bp.route("/challenges")
@jwt_required()
def challenges():
    return render_template("athlete/challenges.html")



@athlete_bp.route("/profile/update", methods=["POST"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # ----- update user basic info -----
    full_name = request.form.get("full_name")
    if full_name:
        user.name = full_name

    # ----- handle athlete profile -----
    profile = AthleteProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = AthleteProfile(user_id=user_id)
        db.session.add(profile)

    profile.age = request.form.get("age") or profile.age
    profile.gender = request.form.get("gender") or profile.gender
    profile.weight = request.form.get("weight") or profile.weight
    profile.height = request.form.get("height") or profile.height

    # ----- update health record (optional latest one) -----
    max_hr = request.form.get("max_hr")
    if max_hr:
        hr = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.desc()).first()
        if not hr:
            hr = HealthRecord(athlete_id=user_id)
            db.session.add(hr)
        hr.heart_rate = max_hr

    # ----- handle profile image -----
    if "profile_image" in request.files:
        file = request.files["profile_image"]
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(filepath)
            user.profile_image = filename

    db.session.commit()
    return jsonify({"msg": "Profile updated successfully", "new_image": user.profile_image}), 200


@athlete_bp.route("/settings/update", methods=["POST"])
@jwt_required()
def update_settings():
    user_id = get_jwt_identity()
    settings = UserSettings.query.filter_by(user_id=user_id).first()

    if not settings:
        settings = UserSettings(user_id=user_id)
        db.session.add(settings)

    settings.notifications = request.form.get("notifications") == "on"
    settings.pin_lock = request.form.get("pin_lock") == "on"
    settings.apple_health = request.form.get("apple_health") == "on"
    settings.dark_mode = request.form.get("dark_mode") == "on"

    db.session.commit()
    return jsonify({"msg": "Settings updated successfully"}), 200