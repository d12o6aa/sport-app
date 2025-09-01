from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.athlete_goals import AthleteGoal
from . import athlete_bp

# Get all goals for an athlete
@athlete_bp.route("/<int:athlete_id>/goals", methods=["GET"])
@jwt_required()
def get_goals(athlete_id):
    goals = AthleteGoal.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{"id": g.id, "title": g.title, "target": g.target_value,
                    "current": g.current_value, "unit": g.unit, "deadline": g.deadline.isoformat() if g.deadline else None}
                    for g in goals])

# Add goal
@athlete_bp.route("/<int:athlete_id>/goals", methods=["POST"])
@jwt_required()
def add_goal(athlete_id):
    data = request.get_json()
    goal = AthleteGoal(
        athlete_id=athlete_id,
        title=data["title"],
        target_value=data["target_value"],
        unit=data.get("unit", ""),
        deadline=data.get("deadline")
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({"msg": "Goal added", "id": goal.id}), 201

# Update goal
@athlete_bp.route("/goals/<int:id>", methods=["PUT"])
@jwt_required()
def update_goal(id):
    goal = AthleteGoal.query.get_or_404(id)
    data = request.get_json()
    goal.title = data.get("title", goal.title)
    goal.target_value = data.get("target_value", goal.target_value)
    goal.current_value = data.get("current_value", goal.current_value)
    goal.unit = data.get("unit", goal.unit)
    db.session.commit()
    return jsonify({"msg": "Goal updated"}), 200

# Delete goal
@athlete_bp.route("/goals/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_goal(id):
    goal = AthleteGoal.query.get_or_404(id)
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"msg": "Goal deleted"}), 200
