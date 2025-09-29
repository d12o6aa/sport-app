from flask import request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.athlete_progress import AthleteProgress
from app.models import Subscription, User
from datetime import datetime, timedelta

from . import athlete_bp

@athlete_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def athlete_dashboard():
    athlete_id = get_jwt_identity()
    if not athlete_id:
        return redirect(url_for('login'))  # Redirect to login if no identity
    user = User.query.get(athlete_id)
    if not user or user.role != 'athlete':
        return jsonify({"msg": "Unauthorized access"}), 403
    return render_template("athlete/progress.html", athlete_id=athlete_id)

@athlete_bp.route("/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_progress(athlete_id):
    if athlete_id != get_jwt_identity():
        return jsonify({"msg": "Unauthorized access"}), 403
    
    period = request.args.get('period', 'week')
    query = AthleteProgress.query.filter_by(athlete_id=athlete_id)
    
    if period == 'week':
        start_date = datetime.now() - timedelta(days=7)
        query = query.filter(AthleteProgress.date >= start_date)
    elif period == 'month':
        start_date = datetime.now() - timedelta(days=30)
        query = query.filter(AthleteProgress.date >= start_date)
    elif period == '3months':
        start_date = datetime.now() - timedelta(days=90)
        query = query.filter(AthleteProgress.date >= start_date)
    
    records = query.order_by(AthleteProgress.date.asc()).all()
    return jsonify([{
        "id": p.id,
        "date": p.date.isoformat(),
        "weight": p.weight,
        "weight_goal": p.weight_goal or 65,
        "calories": p.calories_burned,
        "workouts": p.workouts_done,
        "heart_rate": p.heart_rate or 0,
        "bmi": p.bmi or 0,
        "body_fat": p.body_fat or 0,
        "muscle_mass": p.muscle_mass or 0,
        "protein": p.protein or 0,
        "carbs": p.carbs or 0,
        "fats": p.fats or 0
    } for p in records])

@athlete_bp.route("/<int:athlete_id>/progress", methods=["POST"])
@jwt_required()
def add_progress(athlete_id):
    if athlete_id != get_jwt_identity():
        return jsonify({"msg": "Unauthorized access"}), 403
    
    data = request.get_json()
    progress = AthleteProgress(
        athlete_id=athlete_id,
        weight=data.get("weight"),
        weight_goal=data.get("weight_goal", 65),
        calories_burned=data.get("calories_burned", 0),
        workouts_done=data.get("workouts_done", 0),
        heart_rate=data.get("heart_rate", 0),
        bmi=data.get("bmi", 0),
        body_fat=data.get("body_fat", 0),
        muscle_mass=data.get("muscle_mass", 0),
        protein=data.get("protein", 0),
        carbs=data.get("carbs", 0),
        fats=data.get("fats", 0)
    )
    db.session.add(progress)
    db.session.commit()
    return jsonify({"msg": "Progress added", "id": progress.id}), 201

@athlete_bp.route("/progress/<int:id>", methods=["PUT"])
@jwt_required()
def update_progress(id):
    progress = AthleteProgress.query.get_or_404(id)
    if progress.athlete_id != get_jwt_identity():
        return jsonify({"msg": "Unauthorized access"}), 403
    
    data = request.get_json()
    progress.weight = data.get("weight", progress.weight)
    progress.weight_goal = data.get("weight_goal", progress.weight_goal)
    progress.calories_burned = data.get("calories_burned", progress.calories_burned)
    progress.workouts_done = data.get("workouts_done", progress.workouts_done)
    progress.heart_rate = data.get("heart_rate", progress.heart_rate)
    progress.bmi = data.get("bmi", progress.bmi)
    progress.body_fat = data.get("body_fat", progress.body_fat)
    progress.muscle_mass = data.get("muscle_mass", progress.muscle_mass)
    progress.protein = data.get("protein", progress.protein)
    progress.carbs = data.get("carbs", progress.carbs)
    progress.fats = data.get("fats", progress.fats)
    db.session.commit()
    return jsonify({"msg": "Progress updated"}), 200

@athlete_bp.route("/progress/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_progress(id):
    progress = AthleteProgress.query.get_or_404(id)
    if progress.athlete_id != get_jwt_identity():
        return jsonify({"msg": "Unauthorized access"}), 403
    
    db.session.delete(progress)
    db.session.commit()
    return jsonify({"msg": "Progress deleted"}), 200

@athlete_bp.route("/api/subscription_status", methods=["GET"])
@jwt_required()
def subscription_status():
    athlete_id = get_jwt_identity()
    subscription = Subscription.query.filter_by(user_id=athlete_id, status='active').first()
    return jsonify({
        "success": True,
        "status": subscription.status if subscription else "inactive",
        "plan_name": subscription.plan.name if subscription else None
    })