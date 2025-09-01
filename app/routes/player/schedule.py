from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.athlete_schedule import AthleteSchedule

from . import athlete_bp

@athlete_bp.route("/<int:athlete_id>/schedule", methods=["GET"])
@jwt_required()
def get_schedule(athlete_id):
    items = AthleteSchedule.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{"id": s.id, "title": s.title, "start": s.start_time.isoformat(),
                    "end": s.end_time.isoformat(), "description": s.description}
                    for s in items])

@athlete_bp.route("/<int:athlete_id>/schedule", methods=["POST"])
@jwt_required()
def add_schedule(athlete_id):
    data = request.get_json()
    schedule = AthleteSchedule(
        athlete_id=athlete_id,
        title=data["title"],
        description=data.get("description"),
        start_time=data["start_time"],
        end_time=data["end_time"]
    )
    db.session.add(schedule)
    db.session.commit()
    return jsonify({"msg": "Schedule added", "id": schedule.id}), 201

@athlete_bp.route("/schedule/<int:id>", methods=["PUT"])
@jwt_required()
def update_schedule(id):
    s = AthleteSchedule.query.get_or_404(id)
    data = request.get_json()
    s.title = data.get("title", s.title)
    s.description = data.get("description", s.description)
    s.start_time = data.get("start_time", s.start_time)
    s.end_time = data.get("end_time", s.end_time)
    db.session.commit()
    return jsonify({"msg": "Schedule updated"}), 200

@athlete_bp.route("/schedule/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_schedule(id):
    s = AthleteSchedule.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return jsonify({"msg": "Schedule deleted"}), 200
