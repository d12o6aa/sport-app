from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, WorkoutLog, HealthRecord, WorkoutFile
import os

from . import athlete_bp

def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/log_activity", methods=["GET", "POST"])
@jwt_required()
def log_activity():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        file = request.files.get("file")

        try:
            # Log workout
            if data.get("session_type"):
                workout_log = WorkoutLog(
                    athlete_id=identity,
                    date=datetime.utcnow(),
                    session_type=data.get("session_type"),
                    workout_details={"description": data.get("workout_details")},
                    metrics={"performance_score": float(data.get("performance_score") or 0)},
                    compliance_status="completed",
                    logged_at=datetime.utcnow()
                )
                db.session.add(workout_log)

            # Log health record
            if data.get("weight") or data.get("calories_intake"):
                health_record = HealthRecord(
                    athlete_id=identity,
                    recorded_at=datetime.utcnow(),
                    weight=float(data.get("weight")) if data.get("weight") else None,
                    calories_intake=int(data.get("calories_intake")) if data.get("calories_intake") else None,
                )
                db.session.add(health_record)

            # Log file
            if file and file.filename.endswith(('.jpg', '.png')):
                file_path = os.path.join("uploads/photos", file.filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                workout_file = WorkoutFile(
                    athlete_id=identity,
                    file_path=file_path,
                    file_type="photo",
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(workout_file)

            db.session.commit()
            return jsonify({"msg": "Activity logged successfully!"}), 200  # <-- JSON بدل redirect
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    return render_template("athlete/log_activity.html")
