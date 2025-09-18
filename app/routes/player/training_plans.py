from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required

from . import athlete_bp

@athlete_bp.route("/training_plans", methods=["GET"])
@jwt_required()
def training_plans():
    # Mock data with progress
    plans = [
        {"id": 1, "title": "Strength Boost", "duration_weeks": 6, "description": "Focus on strength training.", "created_at": "2025-09-01"},
        {"id": 2, "title": "Cardio Challenge", "duration_weeks": 4, "description": "Improve endurance.", "created_at": "2025-09-05"}
    ]
    return render_template("athlete/my_plans.html", plans=plans)

@athlete_bp.route("/api/plans", methods=["GET"])
@jwt_required()
def api_plans():
    # Mock API response
    return jsonify([
        {"id": 1, "title": "Strength Boost", "duration_weeks": 6, "description": "Focus on strength training.", "created_at": "2025-09-01"},
        {"id": 2, "title": "Cardio Challenge", "duration_weeks": 4, "description": "Improve endurance.", "created_at": "2025-09-05"}
    ])
