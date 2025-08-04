from flask import Blueprint, jsonify

from app.models.user import User
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import render_template, abort, jsonify

athlete_bp = Blueprint("athlete", __name__)

@athlete_bp.route('/unassigned_athletes', methods=['GET'])
@jwt_required()
def get_unassigned_athletes():
    current_user = get_jwt_identity()
    user = User.query.get(current_user)

    if user.role != 'admin':
        return jsonify({"msg": "Only admins can view unassigned athletes"}), 403

    athletes = User.query.filter_by(role='athlete', coach_id=None).all()
    result = [{"id": a.id, "email": a.email} for a in athletes]
    return jsonify(result)

@athlete_bp.route("/profile")
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != "athlete":
        return abort(403)

    return render_template("athlete/profile.html", user=user)
