from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, CoachAthlete, Feedback

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/view_feedback", methods=["GET"])
@jwt_required()
def view_feedback():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    feedback_list = Feedback.query.filter_by(coach_id=identity).order_by(Feedback.created_at.desc()).all()
    return render_template("coach/view_feedback.html", feedback_list=feedback_list)