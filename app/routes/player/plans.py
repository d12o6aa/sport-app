from datetime import date, timedelta
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.training_plan import TrainingPlan
from . import athlete_bp

@athlete_bp.route("/api/plans", methods=["GET"])
@jwt_required()
def get_plans():
    athlete_id = get_jwt_identity()
    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "duration_weeks": p.duration_weeks,
        "status": p.status
    } for p in plans])

@athlete_bp.route("/api/plans", methods=["POST"])
@jwt_required()
def create_plan():
    athlete_id = get_jwt_identity()
    data = request.get_json()
    plan = TrainingPlan(
        athlete_id=athlete_id,
        coach_id=data.get("coach_id", athlete_id),  # مؤقت
        title=data.get("title"),
        description=data.get("description"),
        duration_weeks=data.get("duration_weeks", 4),
        status=data.get("status", "active"),
        start_date=date.today(),
        end_date=date.today() + timedelta(weeks=data.get("duration_weeks", 4))
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({"msg": "Plan created", "id": plan.id}), 201

@athlete_bp.route("/api/plans/<int:plan_id>", methods=["PUT"])
@jwt_required()
def update_plan(plan_id):
    athlete_id = get_jwt_identity()
    plan = TrainingPlan.query.filter_by(id=plan_id, athlete_id=athlete_id).first_or_404()
    data = request.get_json()
    plan.title = data.get("title", plan.title)
    plan.description = data.get("description", plan.description)
    plan.duration_weeks = data.get("duration_weeks", plan.duration_weeks)
    plan.status = data.get("status", plan.status)
    plan.end_date = plan.start_date + timedelta(weeks=plan.duration_weeks)
    db.session.commit()
    return jsonify({"msg": "Plan updated"})

@athlete_bp.route("/api/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id):
    athlete_id = get_jwt_identity()
    plan = TrainingPlan.query.filter_by(id=plan_id, athlete_id=athlete_id).first_or_404()
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"msg": "Plan deleted"})
