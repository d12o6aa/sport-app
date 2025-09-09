# app/routes/player/health.py
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.readiness_scores import ReadinessScore
from app.models.health_record import HealthRecord
from . import athlete_bp
from datetime import datetime

@athlete_bp.route("/athlete/health", methods=["GET", "POST"])
@jwt_required()
def health_handler():
    user_id = get_jwt_identity()

    if request.method == "GET":
        return handle_get_health(user_id)

    if request.method == "POST":
        return handle_post_health(user_id)


def handle_get_health(user_id):
    records = HealthRecord.query.filter_by(athlete_id=user_id).order_by(HealthRecord.recorded_at.asc()).all()
    data = {
        "weight": format_health_data(records, "weight"),
        "sleep": format_health_data(records, "sleep_hours"),
        "hr": format_health_data(records, "heart_rate"),
        "calIn": format_health_data(records, "calories_intake"),
        "calOut": format_health_data(records, "calories_burned"),
        "bmi": [{"date": r.recorded_at.strftime("%Y-%m-%d"), "value": round(r.weight / ((r.height/100)**2),1)} for r in records if r.weight and r.height],
        "bp_sys": records[-1].bp_sys if records else None,
        "bp_dia": records[-1].bp_dia if records else None,
        "spo2": getattr(records[-1], "spo2", None) if records else None,
        "hrv": getattr(records[-1], "hrv", None) if records else None,
        "mood": getattr(records[-1], "mood", None) if records else None,
        "stress": getattr(records[-1], "stress", None) if records else None,
        "hydration": getattr(records[-1], "hydration", None) if records else None,
    }
    return jsonify(data)


def handle_post_health(user_id):
    data = request.get_json()
    record = HealthRecord(
        athlete_id=user_id,
        recorded_at=datetime.strptime(data.get("date"), "%Y-%m-%d"),
        weight=data.get("weight"),
        height=data.get("height"),
        sleep_hours=data.get("sleep"),
        heart_rate=data.get("hr"),
        calories_intake=data.get("calIn"),
        bp_sys=data.get("bp_sys"),
        bp_dia=data.get("bp_dia"),
    )

    # extra fields لو مضافه عندك في الموديل
    record.calories_burned = data.get("calOut")
    record.spo2 = data.get("spo2")
    record.hrv = data.get("hrv")
    record.mood = data.get("mood")
    record.stress = data.get("stress")
    record.hydration = data.get("hydration")

    db.session.add(record)
    db.session.commit()
    return jsonify({"msg": "Health record added"}), 201


def format_health_data(records, attribute):
    return [
        {"date": r.recorded_at.strftime("%Y-%m-%d"), "value": getattr(r, attribute)}
        for r in records if getattr(r, attribute, None)
    ]
