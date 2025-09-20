from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from app import db
from app.models import User, CoachAthlete, TrainingPlan, Subscription, WorkoutLog, AthleteProgress

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/reports", methods=["GET"])
@jwt_required()
def reports():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Number of members
    num_members = User.query.count()

    # Collective progress (average readiness score)
    avg_progress = db.session.query(func.avg(AthleteProgress.progress)).scalar() or 0

    # Revenues (sum of subscriptions)
    revenues = db.session.query(func.sum(Subscription.amount)).scalar() or 0

    # Coaches performance (average athlete progress per coach)
    coaches_performance = db.session.query(
        User.id.label("coach_id"),
        func.avg(AthleteProgress.progress).label("avg_progress")
    ).join(CoachAthlete, CoachAthlete.coach_id == User.id).join(AthleteProgress, AthleteProgress.athlete_id == CoachAthlete.athlete_id).filter(User.role == "coach").group_by(User.id).all()

    return render_template("admin/reports.html", num_members=num_members, avg_progress=avg_progress, revenues=revenues, coaches_performance=coaches_performance)