# app/routes/training.py
from flask import Blueprint, request, jsonify, render_template, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app import db
from app.models.user import User
from app.models.training import TrainingPlan, Workout, PlanAssignment
from datetime import datetime

training_bp = Blueprint('training', __name__, url_prefix='/training')

# Coach creates a plan
@training_bp.route('/plans', methods=['POST'])
@jwt_required()
def create_plan():
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != 'coach':
        return jsonify({'msg':'Unauthorized'}), 403

    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description', '')

    if not title:
        return jsonify({'msg':'Title is required'}), 400

    plan = TrainingPlan(title=title, description=description, coach_id=coach.id)
    db.session.add(plan)
    db.session.commit()

    return jsonify({'msg':'Plan created', 'plan_id': plan.id}), 201

# Add workouts to a plan (coach)
@training_bp.route('/plans/<int:plan_id>/workouts', methods=['POST'])
@jwt_required()
def add_workout(plan_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    plan = TrainingPlan.query.get_or_404(plan_id)
    if plan.coach_id != coach.id:
        return jsonify({'msg':'Unauthorized'}), 403

    data = request.get_json() or {}
    title = data.get('title')
    description = data.get('description','')
    order = data.get('order', 0)
    duration = data.get('duration_minutes')

    if not title:
        return jsonify({'msg':'Workout title required'}), 400

    w = Workout(plan_id=plan.id, title=title, description=description, order=order, duration_minutes=duration)
    db.session.add(w)
    db.session.commit()
    return jsonify({'msg':'Workout added', 'workout_id': w.id}), 201

# Coach list his plans
@training_bp.route('/coach/plans', methods=['GET'])
@jwt_required()
def coach_plans():
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != 'coach':
        return jsonify({'msg':'Unauthorized'}), 403
    plans = TrainingPlan.query.filter_by(coach_id=coach.id).all()
    result = []
    for p in plans:
        result.append({
            'id': p.id, 'title': p.title, 'description': p.description,
            'created_at': p.created_at.isoformat(),
            'workouts': [{'id': w.id, 'title': w.title, 'order': w.order} for w in p.workouts]
        })
    return jsonify(result), 200

# Assign plan to athlete (coach or admin)
@training_bp.route('/assign', methods=['POST'])
@jwt_required()
def assign_plan():
    identity = get_jwt_identity()
    actor = User.query.get(identity)
    if not actor or actor.role not in ['coach','admin']:
        return jsonify({'msg':'Unauthorized'}), 403

    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    athlete_id = data.get('athlete_id')

    plan = TrainingPlan.query.get(plan_id)
    athlete = User.query.get(athlete_id)
    if not plan or not athlete or athlete.role != 'athlete':
        return jsonify({'msg':'Invalid plan or athlete'}), 400

    # if coach is assigning, ensure they own the plan
    if actor.role == 'coach' and plan.coach_id != actor.id:
        return jsonify({'msg':'Unauthorized to assign this plan'}), 403

    # create or update assignment
    assignment = PlanAssignment.query.filter_by(plan_id=plan.id, athlete_id=athlete.id).first()
    if not assignment:
        assignment = PlanAssignment(plan_id=plan.id, athlete_id=athlete.id)
        db.session.add(assignment)
    else:
        assignment.status = 'assigned'
        assignment.assigned_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'msg':'Plan assigned'}), 200

# Athlete get his assigned plans
@training_bp.route('/my-plans', methods=['GET'])
@jwt_required()
def my_plans():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user or user.role != 'athlete':
        return jsonify({'msg':'Unauthorized'}), 403

    assignments = PlanAssignment.query.filter_by(athlete_id=user.id).all()
    out = []
    for a in assignments:
        p = a.plan
        out.append({
            'assignment_id': a.id,
            'plan': {
                'id': p.id, 'title': p.title, 'description': p.description,
                'workouts': [{'id': w.id, 'title': w.title, 'order': w.order, 'duration_minutes': w.duration_minutes} for w in p.workouts]
            },
            'assigned_at': a.assigned_at.isoformat(),
            'status': a.status
        })
    return jsonify(out), 200

# get plan detail (public to assigned athlete or coach)
@training_bp.route('/plans/<int:plan_id>', methods=['GET'])
@jwt_required()
def get_plan(plan_id):
    identity = get_jwt_identity()
    user = User.query.get(identity)
    plan = TrainingPlan.query.get_or_404(plan_id)

    # allow if coach owner, admin, or athlete assigned
    if user.role == 'coach' and plan.coach_id != user.id:
        return jsonify({'msg':'Unauthorized'}), 403
    if user.role == 'athlete':
        ok = PlanAssignment.query.filter_by(plan_id=plan.id, athlete_id=user.id).first()
        if not ok:
            return jsonify({'msg':'Unauthorized'}), 403

    return jsonify({
        'id': plan.id,
        'title': plan.title,
        'description': plan.description,
        'workouts': [{'id': w.id, 'title': w.title, 'description': w.description, 'order': w.order, 'duration_minutes': w.duration_minutes} for w in plan.workouts]
    }), 200
