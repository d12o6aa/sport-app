from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.athlete_progress import AthleteProgress

from . import athlete_bp

@athlete_bp.route("/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_progress(athlete_id):
    records = AthleteProgress.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{"id": p.id, "date": p.date.isoformat(),
                     "weight": p.weight, "calories": p.calories_burned, "workouts": p.workouts_done}
                    for p in records])

@athlete_bp.route("/<int:athlete_id>/progress", methods=["POST"])
@jwt_required()
def add_progress(athlete_id):
    data = request.get_json()
    progress = AthleteProgress(
        athlete_id=athlete_id,
        weight=data.get("weight"),
        calories_burned=data.get("calories_burned"),
        workouts_done=data.get("workouts_done", 0)
    )
    db.session.add(progress)
    db.session.commit()
    return jsonify({"msg": "Progress added", "id": progress.id}), 201

@athlete_bp.route("/progress/<int:id>", methods=["PUT"])
@jwt_required()
def update_progress(id):
    p = AthleteProgress.query.get_or_404(id)
    data = request.get_json()
    p.weight = data.get("weight", p.weight)
    p.calories_burned = data.get("calories_burned", p.calories_burned)
    p.workouts_done = data.get("workouts_done", p.workouts_done)
    db.session.commit()
    return jsonify({"msg": "Progress updated"}), 200

@athlete_bp.route("/progress/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_progress(id):
    p = AthleteProgress.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"msg": "Progress deleted"}), 200
