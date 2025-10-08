from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from app import db
from app.models import User, CoachAthlete, TrainingPlan, WorkoutSession, NutritionPlan
from sqlalchemy import desc, and_, or_
import os
from werkzeug.utils import secure_filename
from . import coach_bp

UPLOAD_FOLDER = 'static/uploads/plans'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/training-plans", methods=["GET"])
@jwt_required()
def training_plans_management():
    """Main training plans management page for coaches"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Get all active athletes
    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    
    return render_template("coach/training_plans.html", athletes=athletes)

@coach_bp.route("/api/training-plans", methods=["GET"])
@jwt_required()
def get_all_plans():
    """Get all training plans for coach's athletes"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athlete_id = request.args.get('athlete_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base query
    query = (
        db.session.query(TrainingPlan)
        .filter(TrainingPlan.coach_id == identity)
    )

    # Apply filters
    if athlete_id:
        query = query.filter(TrainingPlan.athlete_id == athlete_id)
    
    if status and status != 'all':
        query = query.filter(TrainingPlan.status == status)
    
    if start_date:
        query = query.filter(TrainingPlan.start_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    
    if end_date:
        query = query.filter(TrainingPlan.end_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    plans = query.order_by(desc(TrainingPlan.created_at)).all()

    result = []
    for plan in plans:
        plan_dict = {
            'id': plan.id,
            'athlete_id': plan.athlete_id,
            'athlete_name': plan.athlete.name if plan.athlete else 'Unknown',
            'title': plan.title,
            'description': plan.description,
            'start_date': plan.start_date.isoformat(),
            'end_date': plan.end_date.isoformat() if plan.end_date else None,
            'duration_weeks': plan.duration_weeks,
            'status': plan.status,
            'image_url': plan.image_url,
            'exercises': plan.exercises or {},
            'created_at': plan.created_at.isoformat() if plan.created_at else None
        }
        
        # Count associated workouts
        workout_count = WorkoutSession.query.filter_by(plan_id=plan.id).count() if hasattr(WorkoutSession, 'plan_id') else 0
        plan_dict['workout_count'] = workout_count
        
        result.append(plan_dict)

    return jsonify(result), 200

@coach_bp.route("/api/training-plans/<int:plan_id>", methods=["GET"])
@jwt_required()
def get_plan_detail(plan_id):
    """Get detailed training plan information"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first()

    if not plan:
        return jsonify({"msg": "Plan not found"}), 404

    plan_dict = {
        'id': plan.id,
        'athlete_id': plan.athlete_id,
        'athlete_name': plan.athlete.name if plan.athlete else 'Unknown',
        'athlete_email': plan.athlete.email if plan.athlete else 'Unknown',
        'title': plan.title,
        'description': plan.description,
        'start_date': plan.start_date.isoformat(),
        'end_date': plan.end_date.isoformat() if plan.end_date else None,
        'duration_weeks': plan.duration_weeks,
        'status': plan.status,
        'image_url': plan.image_url,
        'exercises': plan.exercises or {},
        'created_at': plan.created_at.isoformat() if plan.created_at else None
    }

    return jsonify(plan_dict), 200

@coach_bp.route("/api/training-plans", methods=["POST"])
@jwt_required()
def create_plan():
    """Create a new training plan for an athlete"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        athlete_id = request.form.get('athlete_id', type=int)
        
        if not athlete_id:
            return jsonify({"msg": "Athlete ID is required"}), 400

        # Verify coach has access to this athlete
        link = CoachAthlete.query.filter_by(
            coach_id=identity, 
            athlete_id=athlete_id, 
            is_active=True
        ).first()
        
        if not link:
            return jsonify({"msg": "Not authorized for this athlete"}), 403

        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().timestamp()}_{file.filename}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                image_url = f'/static/uploads/plans/{filename}'

        # Parse exercises if provided
        exercises = {}
        exercises_str = request.form.get('exercises')
        if exercises_str:
            import json
            exercises = json.loads(exercises_str)

        # Calculate duration in weeks
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get('end_date') else None
        
        duration_weeks = 4  # Default
        if end_date:
            duration_weeks = max(1, (end_date - start_date).days // 7)

        # Create plan
        plan = TrainingPlan(
            coach_id=identity,
            athlete_id=athlete_id,
            title=request.form.get('title', 'Untitled Plan'),
            description=request.form.get('description'),
            start_date=start_date,
            end_date=end_date,
            duration_weeks=duration_weeks,
            status=request.form.get('status', 'active'),
            image_url=image_url,
            exercises=exercises,
            created_at=datetime.utcnow()
        )

        db.session.add(plan)
        db.session.commit()

        result = {
            'id': plan.id,
            'athlete_name': plan.athlete.name,
            'title': plan.title,
            'status': plan.status
        }

        return jsonify({"msg": "Training plan created successfully", "plan": result}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error creating plan: {str(e)}"}), 500

@coach_bp.route("/api/training-plans/<int:plan_id>", methods=["PUT"])
@jwt_required()
def update_plan(plan_id):
    """Update an existing training plan"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first()

        if not plan:
            return jsonify({"msg": "Plan not found"}), 404

        # Update fields
        if 'title' in request.form:
            plan.title = request.form['title']
        if 'description' in request.form:
            plan.description = request.form['description']
        if 'start_date' in request.form:
            plan.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        if 'end_date' in request.form:
            plan.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date() if request.form['end_date'] else None
        if 'status' in request.form:
            plan.status = request.form['status']
        if 'duration_weeks' in request.form:
            plan.duration_weeks = int(request.form['duration_weeks'])

        # Update exercises
        exercises_str = request.form.get('exercises')
        if exercises_str:
            import json
            plan.exercises = json.loads(exercises_str)

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{plan.athlete_id}_{datetime.now().timestamp()}_{file.filename}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                plan.image_url = f'/static/uploads/plans/{filename}'

        db.session.commit()

        result = {
            'id': plan.id,
            'athlete_name': plan.athlete.name,
            'title': plan.title,
            'status': plan.status
        }

        return jsonify({"msg": "Plan updated successfully", "plan": result}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error updating plan: {str(e)}"}), 500

@coach_bp.route("/api/training-plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id):
    """Delete a training plan"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first()

        if not plan:
            return jsonify({"msg": "Plan not found"}), 404

        db.session.delete(plan)
        db.session.commit()

        return jsonify({"msg": "Plan deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error deleting plan: {str(e)}"}), 500

@coach_bp.route("/api/training-plans/<int:plan_id>/duplicate", methods=["POST"])
@jwt_required()
def duplicate_plan(plan_id):
    """Duplicate an existing training plan"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        original_plan = TrainingPlan.query.filter_by(id=plan_id, coach_id=identity).first()

        if not original_plan:
            return jsonify({"msg": "Plan not found"}), 404

        # Get new athlete_id from request
        new_athlete_id = request.form.get('athlete_id', type=int)
        if not new_athlete_id:
            new_athlete_id = original_plan.athlete_id

        # Create duplicate
        new_plan = TrainingPlan(
            coach_id=identity,
            athlete_id=new_athlete_id,
            title=f"{original_plan.title} (Copy)",
            description=original_plan.description,
            start_date=date.today(),
            end_date=None,
            duration_weeks=original_plan.duration_weeks,
            status='active',
            image_url=original_plan.image_url,
            exercises=original_plan.exercises.copy() if original_plan.exercises else {},
            created_at=datetime.utcnow()
        )

        db.session.add(new_plan)
        db.session.commit()

        return jsonify({"msg": "Plan duplicated successfully", "plan_id": new_plan.id}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error duplicating plan: {str(e)}"}), 500

@coach_bp.route("/api/athletes/<int:athlete_id>/plan-stats", methods=["GET"])
@jwt_required()
def get_athlete_plan_stats(athlete_id):
    """Get training plan statistics for a specific athlete"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify access
    link = CoachAthlete.query.filter_by(
        coach_id=identity, 
        athlete_id=athlete_id, 
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not authorized for this athlete"}), 403

    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id, coach_id=identity).all()
    
    if not plans:
        return jsonify({
            "total_plans": 0,
            "active_plans": 0,
            "completed_plans": 0,
            "avg_duration_weeks": 0
        }), 200

    active = [p for p in plans if p.status == 'active']
    completed = [p for p in plans if p.status == 'completed']
    
    stats = {
        "total_plans": len(plans),
        "active_plans": len(active),
        "completed_plans": len(completed),
        "archived_plans": len([p for p in plans if p.status == 'archived']),
        "avg_duration_weeks": round(sum(p.duration_weeks for p in plans) / len(plans), 1) if plans else 0,
        "oldest_plan_date": min(p.start_date for p in plans).isoformat() if plans else None,
        "newest_plan_date": max(p.start_date for p in plans).isoformat() if plans else None
    }

    return jsonify(stats), 200