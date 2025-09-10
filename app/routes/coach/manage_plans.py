from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, TrainingPlan

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/manage_plans", methods=["GET", "POST"])
@jwt_required()
def manage_plans():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        athlete_id = data.get("athlete_id")
        title = data.get("title")
        description = data.get("description")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
        if not link:
            return jsonify({"msg": "Not your athlete"}), 403

        try:
            plan = TrainingPlan(
                athlete_id=athlete_id,
                title=title,
                description=description,
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d") if end_date else None,
                status="active",
                created_at=datetime.utcnow()
            )
            db.session.add(plan)
            db.session.commit()
            flash("Plan created successfully!", "success")
            return redirect(url_for("manage_plans.manage_plans"))
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    plans = (
        db.session.query(TrainingPlan)
        .join(CoachAthlete, CoachAthlete.athlete_id == TrainingPlan.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .order_by(TrainingPlan.start_date.desc())
        .all()
    )
    return render_template("coach/manage_plans.html", athletes=athletes, plans=plans)