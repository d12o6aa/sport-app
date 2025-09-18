from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, HealthIntegration

from . import athlete_bp

def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/integrations", methods=["GET", "POST"])
@jwt_required()
def integrations():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        provider = data.get("provider")
        steps = data.get("steps")
        calories = data.get("calories")

        try:
            integration = HealthIntegration(
                athlete_id=identity,
                provider=provider,
                steps=int(steps) if steps else None,
                calories=int(calories) if calories else None,
                recorded_at=datetime.utcnow()
            )
            db.session.add(integration)
            db.session.commit()
            flash("Health data logged successfully!", "success")
            return redirect(url_for("integrations.integrations"))
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Error: {str(e)}"}), 500

    integrations = HealthIntegration.query.filter_by(athlete_id=identity).order_by(HealthIntegration.recorded_at.desc()).limit(10).all()
    return render_template("athlete/integrations.html", integrations=integrations)