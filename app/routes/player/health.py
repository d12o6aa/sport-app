# app/routes/player/health.py
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.readiness_scores import ReadinessScore
from . import athlete_bp

@athlete_bp.route("/api/health", methods=["GET"])
@jwt_required()
def get_health():
    athlete_id = get_jwt_identity()
    scores = ReadinessScore.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{
        "id": h.id,
        "date": h.date.isoformat(),
        "sleep_hours": h.sleep_hours,
        "resting_hr": h.resting_hr,
        "hrv": h.hrv,
        "fatigue_level": h.fatigue_level
    } for h in scores])

@athlete_bp.route("/api/health", methods=["POST"])
@jwt_required()
def create_health():
    athlete_id = get_jwt_identity()
    data = request.get_json()
    score = ReadinessScore(
        athlete_id=athlete_id,
        sleep_hours=data.get("sleep_hours"),
        resting_hr=data.get("resting_hr"),
        hrv=data.get("hrv"),
        fatigue_level=data.get("fatigue_level")
    )
    db.session.add(score)
    db.session.commit()
    return jsonify({"msg": "Health record added", "id": score.id}), 201
