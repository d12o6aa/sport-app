from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, CoachAthlete, Feedback

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/select_feedback", methods=["GET"])
@jwt_required()
def select_feedback():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athlete_id = request.args.get("athlete_id")
    feedback_type = request.args.get("type")

    query = Feedback.query.filter_by(coach_id=identity)
    if athlete_id:
        query = query.filter_by(athlete_id=athlete_id)
    if feedback_type:
        query = query.filter_by(type=feedback_type)

    feedback_list = query.order_by(Feedback.created_at.desc()).all()
    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/select_feedback.html", feedback_list=feedback_list, athletes=athletes, selected_athlete=athlete_id, selected_type=feedback_type)