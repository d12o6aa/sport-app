# app/routes/player/workouts.py
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.workout_log import WorkoutLog
from . import athlete_bp

@athlete_bp.route("/api/workouts", methods=["GET"])
@jwt_required()
def get_workouts():
    athlete_id = get_jwt_identity()
    logs = WorkoutLog.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{
        "id": w.id,
        "title": w.session_type,           # لو حابة title يبقى session_type
        "type": w.session_type,            # type دلوقتي هي session_type
        "intensity": w.compliance_status, # intensity ممكن تربطيها بحاجة مناسبة
        "date": w.date.isoformat(),
        "notes": w.feedback               # notes بقى feedback
    } for w in logs])
@athlete_bp.route("/api/workouts", methods=["POST"])
@jwt_required()
def create_workout():
    athlete_id = get_jwt_identity()
    data = request.get_json()
    log = WorkoutLog(
        athlete_id=athlete_id,
        session_type=data.get("session_type", "strength"),
        duration=data.get("duration"),
        metrics=data.get("metrics", {}),
        feedback=data.get("feedback"),
        compliance_status=data.get("compliance_status", "completed")
    )

    db.session.add(log)
    db.session.commit()
    return jsonify({"msg": "Workout logged", "id": log.id}), 201

@athlete_bp.route("/api/workouts/<int:log_id>", methods=["PUT"])
@jwt_required()
def update_workout(log_id):
    athlete_id = get_jwt_identity()
    log = WorkoutLog.query.filter_by(id=log_id, athlete_id=athlete_id).first_or_404()
    data = request.get_json()
    log.session_type = data.get("session_type", log.session_type)
    log.duration = data.get("duration", log.duration)
    log.metrics = data.get("metrics", log.metrics)
    log.feedback = data.get("feedback", log.feedback)
    log.compliance_status = data.get("compliance_status", log.compliance_status)
    db.session.commit()
    return jsonify({"msg": "Workout updated"})

@athlete_bp.route("/api/workouts/<int:log_id>", methods=["DELETE"])
@jwt_required()
def delete_workout(log_id):
    athlete_id = get_jwt_identity()
    log = WorkoutLog.query.filter_by(id=log_id, athlete_id=athlete_id).first_or_404()
    db.session.delete(log)
    db.session.commit()
    return jsonify({"msg": "Workout deleted"})
