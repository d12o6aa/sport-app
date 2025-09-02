from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.athlete_goals import AthleteGoal
from . import athlete_bp
from datetime import date

# ---------------- API: Get all goals ----------------
@athlete_bp.route("/api/goals", methods=["GET"])
@jwt_required()
def get_goals():
    user_id = get_jwt_identity()
    goals = AthleteGoal.query.filter_by(athlete_id=user_id).all()
    return jsonify([
        {
            "id": g.id,
            "title": g.title,
            "target": g.target_value,   # <-- استخدم target_value
            "current_value": g.current_value,
            "unit": g.unit,
            "due_date": g.deadline.isoformat() if g.deadline else None,
            "created_at": g.created_at.isoformat(),
        } for g in goals
    ])

# ---------------- API: Create goal ----------------
@athlete_bp.route("/api/goals", methods=["POST"])
@jwt_required()
def create_goal():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data.get("title"):
        return jsonify({"msg": "Title is required"}), 400

    deadline = None
    if data.get("due_date"):
        try:
            deadline = date.fromisoformat(data["due_date"])
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400

    goal = AthleteGoal(
        athlete_id=user_id,   # <-- هنا صح
        title=data["title"],
        target_value=data.get("target", 0),  # <-- اربط بالعمود الصحيح
        current_value=0.0,
        unit="",
        deadline=deadline
    )
    db.session.add(goal)
    db.session.commit()
    return jsonify({"msg": "Goal created", "id": goal.id}), 201

# ---------------- API: Update goal ----------------
@athlete_bp.route("/api/goals/<int:goal_id>", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    user_id = get_jwt_identity()
    goal = AthleteGoal.query.filter_by(id=goal_id, athlete_id=user_id).first_or_404()
    data = request.get_json()

    if "due_date" in data and data["due_date"]:
        try:
            goal.deadline = date.fromisoformat(data["due_date"])
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400

    goal.title = data.get("title", goal.title)
    goal.target_value = data.get("target", goal.target_value)
    goal.current_value = data.get("current_value", goal.current_value)
    goal.unit = data.get("unit", goal.unit)

    db.session.commit()
    return jsonify({"msg": "Goal updated"})

# ---------------- API: Delete goal ----------------
@athlete_bp.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    user_id = get_jwt_identity()
    goal = AthleteGoal.query.filter_by(id=goal_id, athlete_id=user_id).first_or_404()

    db.session.delete(goal)
    db.session.commit()
    return jsonify({"msg": "Goal deleted"})
