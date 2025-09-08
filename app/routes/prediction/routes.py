from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import MLInsight, ReadinessScore
from app.routes.prediction.service import predict_all  # ده الفنكشن اللي بيرجع نتائج الموديل

prediction_bp = Blueprint("prediction", __name__, url_prefix="/prediction")

@prediction_bp.route("/run", methods=["POST"])
@jwt_required()
def run_prediction():
    user_id = get_jwt_identity()
    input_data = request.get_json()

    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        # call ML service
        result = predict_all(input_data)

        # -------- تخزين في MLInsight --------
        insight = MLInsight(
            athlete_id=user_id,
            generated_at=datetime.utcnow(),
            insight_data=result
        )
        db.session.add(insight)

        # -------- تخزين readiness (لو عايزة تعرضه في الداشبورد) --------
        readiness_score = result.get("performance_class")
        if readiness_score is not None:
            rs = ReadinessScore(
                athlete_id=user_id,
                date=datetime.utcnow().date(),
                score=int(readiness_score),
                injury_risk=str(result.get("injury_severity_prediction")),
                recovery_prediction=str(result.get("recovery_success_prediction"))
            )
            db.session.add(rs)

        db.session.commit()

        return jsonify({
            "message": "Prediction stored successfully",
            "result": result
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
