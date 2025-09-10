from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, WorkoutSession

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/create_workout", methods=["GET", "POST"])
@jwt_required()
def create_workout():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        athlete_id = data.get("athlete_id")
        name = data.get("name")
        type = data.get("type")
        duration = data.get("duration")
        performed_at = data.get("performed_at")

        link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
        if not link:
            return jsonify({"msg": "Not your athlete"}), 403

        try:
            workout = WorkoutSession(
                athlete_id=athlete_id,
                name=name,
                type=type,
                duration=int(duration) if duration else None,
                performed_at=datetime.strptime(performed_at, "%Y-%m-%d"),
                created_at=datetime.utcnow()
            )
            db.session.add(workout)
            db.session.commit()
            flash("Workout created successfully!", "success")
            return redirect(url_for("create_workout.create_workout"))
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/create_workout.html", athletes=athletes)