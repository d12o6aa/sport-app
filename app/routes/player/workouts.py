from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app.extensions import db
from app.models.workout_log import WorkoutLog
from app.models.exercises import Exercise
from app.models.workout_log_exercises import WorkoutLogExercise
import os
from werkzeug.utils import secure_filename
from datetime import datetime

from . import athlete_bp
UPLOAD_FOLDER = 'app/static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@athlete_bp.route("/api/workouts", methods=["GET"])
def get_workouts():
    try:
        # دعم Header أو Cookie
        verify_jwt_in_request()
        athlete_id = get_jwt_identity()
        logs = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(WorkoutLog.date.desc()).all()
        return jsonify([{
            "id": w.id,
            "title": w.session_type,
            "type": w.session_type,
            "intensity": w.compliance_status,
            "date": w.date.isoformat(),
            "notes": w.feedback,
            "level": w.workout_details.get("level", "beginner"),
            "duration": w.workout_details.get("duration", 0),
            "calories": w.workout_details.get("calories", 0),
            "image_url": w.workout_details.get("image_url")
        } for w in logs])
    except Exception as e:
        return jsonify({"msg": str(e)}), 401

@athlete_bp.route("/api/workouts", methods=["POST"])
def create_workout():
    try:
        verify_jwt_in_request()
        athlete_id = get_jwt_identity()
        if 'image' not in request.files:
            return jsonify({"msg": "No image provided"}), 400
        file = request.files['image']
        if file.filename == '':
            return jsonify({"msg": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{athlete_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_url = f"/static/uploads/{filename}"
        else:
            image_url = None

        data = request.form
        new_log = WorkoutLog(
            athlete_id=athlete_id,
            session_type=data.get("title", "Strength"),
            feedback=data.get("notes"),
            compliance_status=data.get("intensity", "completed"),
            date=data.get("date"),
            metrics={},
            workout_details={
                "level": data.get("level", "beginner"),
                "duration": int(data.get("duration", 0)),
                "calories": int(data.get("calories", 0)),
                "image_url": image_url
            }
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"msg": "Workout logged successfully!", "id": new_log.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/<int:log_id>", methods=["PUT"])
def update_workout(log_id):
    try:
        verify_jwt_in_request()
        athlete_id = get_jwt_identity()
        log = WorkoutLog.query.filter_by(id=log_id, athlete_id=athlete_id).first_or_404()
        data = request.form
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_url = f"/static/uploads/{filename}"
                if not log.workout_details:
                    log.workout_details = {}
                log.workout_details["image_url"] = image_url

        log.session_type = data.get("title", log.session_type)
        log.feedback = data.get("notes", log.feedback)
        log.compliance_status = data.get("intensity", log.compliance_status)
        log.date = data.get("date", log.date)
        if not log.workout_details:
            log.workout_details = {}
        log.workout_details.update({
            "level": data.get("level", log.workout_details.get("level", "beginner")),
            "duration": int(data.get("duration", log.workout_details.get("duration", 0))),
            "calories": int(data.get("calories", log.workout_details.get("calories", 0)))
        })
        db.session.commit()
        return jsonify({"msg": "Workout updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/<int:log_id>", methods=["DELETE"])
def delete_workout(log_id):
    try:
        verify_jwt_in_request()
        athlete_id = get_jwt_identity()
        log = WorkoutLog.query.filter_by(id=log_id, athlete_id=athlete_id).first_or_404()
        db.session.delete(log)
        db.session.commit()
        return jsonify({"msg": "Workout deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/exercises", methods=["GET"])
def get_exercises():
    try:
        verify_jwt_in_request()
        exercises = Exercise.query.all()
        return jsonify([e.to_dict() for e in exercises])
    except Exception as e:
        return jsonify({"msg": str(e)}), 401

@athlete_bp.route("/api/add_exercise_to_workout", methods=["POST"])
def add_exercise_to_workout():
    try:
        verify_jwt_in_request()
        athlete_id = get_jwt_identity()
        data = request.get_json()
        exercise_id = data.get("exercise_id")
        
        exercise = Exercise.query.get(exercise_id)
        if not exercise:
            return jsonify({"msg": "Exercise not found"}), 404
        
        log = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(WorkoutLog.date.desc()).first()
        if log:
            new_log_exercise = WorkoutLogExercise(
                workout_log_id=log.id,
                exercise_id=exercise.id,
                sets=3,
                reps=10,
                weight=0.0,
                duration_minutes=exercise.duration // 60 if exercise.duration else 0
            )
            db.session.add(new_log_exercise)
            if not log.workout_details or not log.workout_details.get("image_url"):
                log.workout_details = {"image_url": exercise.image_url} if exercise.image_url else log.workout_details
            db.session.commit()
        else:
            new_log = WorkoutLog(
                athlete_id=athlete_id,
                session_type="Custom",
                feedback=f"Included exercise: {exercise.name}",
                compliance_status="partial",
                workout_details={
                    "level": "beginner",
                    "duration": exercise.duration // 60 if exercise.duration else 0,
                    "calories": exercise.calories or 0,
                    "image_url": exercise.image_url
                }
            )
            db.session.add(new_log)
            db.session.flush()
            new_log_exercise = WorkoutLogExercise(
                workout_log_id=new_log.id,
                exercise_id=exercise.id,
                sets=3,
                reps=10,
                weight=0.0,
                duration_minutes=exercise.duration // 60 if exercise.duration else 0
            )
            db.session.add(new_log_exercise)
            db.session.commit()
        
        return jsonify({"msg": "Exercise added to your log!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400