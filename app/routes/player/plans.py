from datetime import date, timedelta
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.training_plan import TrainingPlan
from . import athlete_bp
import os
from werkzeug.utils import secure_filename
from flask import current_app


UPLOAD_FOLDER = "static/uploads"

@athlete_bp.route("/api/plans", methods=["GET"])
@jwt_required()
def get_plans():
    athlete_id = get_jwt_identity()
    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id).all()
    
    # ✅ FIX: تأكد من إرجاع حقل التقدم (Progress)
    return jsonify([{
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "duration_weeks": p.duration_weeks,
        "status": p.status,
        "image_url": p.image_url,
        "progress": p.progress if hasattr(p, 'progress') else 0, # Assuming 'progress' exists in the model
        "start_date": p.start_date.isoformat() if p.start_date else None,
        "end_date": p.end_date.isoformat() if p.end_date else None
    } for p in plans])

@athlete_bp.route("/api/plans", methods=["POST"])
@jwt_required()
def create_plan():
    athlete_id = get_jwt_identity()
    data = request.form

    # معالجة الصورة
    image_file = request.files.get("image")
    image_url = None
    if image_file:
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        image_file.save(save_path)
        image_url = f"/{UPLOAD_FOLDER}/{filename}"

    plan = TrainingPlan(
        athlete_id=athlete_id,
        coach_id=data.get("coach_id", athlete_id), # استخدام athlete_id كـ coach_id افتراضي مؤقتًا
        title=data.get("title"),
        description=data.get("description"),
        duration_weeks=int(data.get("duration_weeks", 4)),
        status=data.get("status", "active"),
        start_date=date.today(),
        end_date=date.today() + timedelta(weeks=int(data.get("duration_weeks", 4))),
        image_url=image_url,
        # ✅ يتم تعيين التقدم الأولي على 0%
        progress=0 
    )
    db.session.add(plan)
    db.session.commit()
    return jsonify({"msg": "Plan created", "id": plan.id, "image_url": image_url}), 201

@athlete_bp.route("/api/plans/<int:plan_id>", methods=["PUT"])
@jwt_required()
def update_plan(plan_id):
    athlete_id = get_jwt_identity()
    plan = TrainingPlan.query.filter_by(id=plan_id, athlete_id=athlete_id).first_or_404()
    data = request.form

    # ✅ FIX: تحديث حقل التقدم
    progress_value = data.get("progress")
    if progress_value is not None:
        try:
            plan.progress = int(float(progress_value))
        except ValueError:
            pass 

    plan.title = data.get("title", plan.title)
    plan.description = data.get("description", plan.description)
    plan.duration_weeks = int(data.get("duration_weeks", plan.duration_weeks))
    plan.status = data.get("status", plan.status)
    plan.end_date = plan.start_date + timedelta(weeks=plan.duration_weeks)

    image_file = request.files.get("image")
    if image_file:
        filename = secure_filename(image_file.filename)
        save_path = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        image_file.save(save_path)
        plan.image_url = f"/{UPLOAD_FOLDER}/{filename}"

    db.session.commit()
    return jsonify({"msg": "Plan updated", "image_url": plan.image_url, "progress": plan.progress if hasattr(plan, 'progress') else 0})


@athlete_bp.route("/api/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id):
    athlete_id = get_jwt_identity()
    plan = TrainingPlan.query.filter_by(id=plan_id, athlete_id=athlete_id).first_or_404()
    db.session.delete(plan)
    db.session.commit()
    return jsonify({"msg": "Plan deleted"})