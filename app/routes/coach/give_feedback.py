from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, Feedback

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/give_feedback", methods=["GET", "POST"])
@jwt_required()
def give_feedback():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        athlete_id = data.get("athlete_id")
        content = data.get("content")
        feedback_type = data.get("type")

        link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
        if not link:
            return jsonify({"msg": "Not your athlete"}), 403

        try:
            feedback = Feedback(
                coach_id=identity,
                athlete_id=athlete_id,
                content=content,
                type=feedback_type,
                created_at=datetime.utcnow()
            )
            db.session.add(feedback)
            db.session.commit()
            flash("Feedback sent successfully!", "success")
            return redirect(url_for("give_feedback.give_feedback"))
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/give_feedback.html", athletes=athletes)