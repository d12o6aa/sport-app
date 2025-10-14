from flask import Blueprint, request, jsonify, render_template, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from app import db
from app.models import User, CoachAthlete, WorkoutLog
from sqlalchemy import desc, and_, or_
import os
from werkzeug.utils import secure_filename
import json

from . import coach_bp

UPLOAD_FOLDER = 'static/uploads/workouts'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/workouts", methods=["GET"])
@jwt_required()
def workout_management():
    """Main workout management page for coaches"""
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
    
    return render_template("coach/workout_management.html", athletes=athletes)

@coach_bp.route("/api/workouts", methods=["GET"])
@jwt_required()
def get_all_workouts():
    """Get all workouts for coach's athletes"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athlete_id = request.args.get('athlete_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    workout_type = request.args.get('workout_type')

    # Base query - get workouts for all coach's athletes
    query = (
        db.session.query(WorkoutLog)
        .join(CoachAthlete, CoachAthlete.athlete_id == WorkoutLog.athlete_id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
    )

    # Apply filters
    if athlete_id:
        query = query.filter(WorkoutLog.athlete_id == athlete_id)
    
    if start_date_str:
        query = query.filter(WorkoutLog.date >= datetime.strptime(start_date_str, '%Y-%m-%d').date())
    
    if end_date_str:
        query = query.filter(WorkoutLog.date <= datetime.strptime(end_date_str, '%Y-%m-%d').date())
    
    if workout_type and workout_type != 'all':
        query = query.filter(WorkoutLog.workout_type == workout_type)

    workouts = query.order_by(desc(WorkoutLog.date), desc(WorkoutLog.logged_at)).all()

    result = []
    for workout in workouts:
        workout_dict = workout.to_dict()
        workout_dict['athlete_name'] = workout.athlete.name if workout.athlete else 'Unknown'
        result.append(workout_dict)

    return jsonify(result), 200

@coach_bp.route("/api/workouts/<int:workout_id>", methods=["GET"])
@jwt_required()
def get_workout_detail(workout_id):
    """Get detailed workout information"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    workout = (
        db.session.query(WorkoutLog)
        .join(CoachAthlete, CoachAthlete.athlete_id == WorkoutLog.athlete_id)
        .filter(
            WorkoutLog.id == workout_id,
            CoachAthlete.coach_id == identity,
            CoachAthlete.is_active == True
        )
        .first()
    )

    if not workout:
        return jsonify({"msg": "Workout not found"}), 404

    workout_dict = workout.to_dict()
    workout_dict['athlete_name'] = workout.athlete.name if workout.athlete else 'Unknown'
    workout_dict['athlete_email'] = workout.athlete.email if workout.athlete else 'Unknown'

    return jsonify(workout_dict), 200

@coach_bp.route("/api/workouts", methods=["POST"])
@jwt_required()
def create_workout():
    """Create a new workout for an athlete"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        athlete_id = request.form.get('athlete_id', type=int)
        
        if not athlete_id:
            return jsonify({"msg": "Athlete ID is required"}), 400

        link = CoachAthlete.query.filter_by(
            coach_id=identity, 
            athlete_id=athlete_id, 
            is_active=True
        ).first()
        
        if not link:
            return jsonify({"msg": "Not authorized for this athlete"}), 403

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().timestamp()}_{file.filename}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                image_url = f'/static/uploads/workouts/{filename}'

        # Get workout type from form
        workout_type_value = request.form.get('workout_type', 'other')
        custom_workout_type = request.form.get('custom_workout_type', None)
        
        # Use custom type if provided and generic type is 'other'
        final_workout_type = custom_workout_type if workout_type_value == 'other' and custom_workout_type else workout_type_value

        workout = WorkoutLog(
            athlete_id=athlete_id,
            title=request.form.get('title', 'Untitled Workout'),
            workout_type=final_workout_type,
            session_type='workout',
            planned_duration=request.form.get('planned_duration', type=int),
            actual_duration=request.form.get('actual_duration', type=int),
            calories_burned=request.form.get('calories_burned', 0, type=int),
            avg_heart_rate=request.form.get('avg_heart_rate', type=int),
            max_heart_rate=request.form.get('max_heart_rate', type=int),
            recovery_time=request.form.get('recovery_time', type=int),
            completion_status=request.form.get('completion_status', 'completed'),
            difficulty_level=request.form.get('difficulty_level', 'beginner'),
            notes=request.form.get('notes'),
            image_url=image_url,
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date() if request.form.get('date') else date.today(),
            logged_at=datetime.utcnow()
        )

        db.session.add(workout)
        db.session.commit()

        result = workout.to_dict()
        result['athlete_name'] = workout.athlete.name

        return jsonify({"msg": "Workout created successfully", "workout": result}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error creating workout: {str(e)}"}), 500

@coach_bp.route("/api/workouts/<int:workout_id>", methods=["PUT"])
@jwt_required()
def update_workout(workout_id):
    """Update an existing workout"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        workout = (
            db.session.query(WorkoutLog)
            .join(CoachAthlete, CoachAthlete.athlete_id == WorkoutLog.athlete_id)
            .filter(
                WorkoutLog.id == workout_id,
                CoachAthlete.coach_id == identity,
                CoachAthlete.is_active == True
            )
            .first()
        )

        if not workout:
            return jsonify({"msg": "Workout not found"}), 404

        # Get workout type from form
        workout_type_value = request.form.get('workout_type', 'other')
        custom_workout_type = request.form.get('custom_workout_type', None)
        
        final_workout_type = custom_workout_type if workout_type_value == 'other' and custom_workout_type else workout_type_value

        if 'title' in request.form:
            workout.title = request.form['title']
        if 'workout_type' in request.form:
            workout.workout_type = final_workout_type
        if 'planned_duration' in request.form:
            workout.planned_duration = int(request.form['planned_duration'])
        if 'actual_duration' in request.form:
            workout.actual_duration = int(request.form['actual_duration'])
        if 'calories_burned' in request.form:
            workout.calories_burned = int(request.form['calories_burned'])
        if 'avg_heart_rate' in request.form:
            workout.avg_heart_rate = int(request.form['avg_heart_rate']) if request.form['avg_heart_rate'] else None
        if 'max_heart_rate' in request.form:
            workout.max_heart_rate = int(request.form['max_heart_rate']) if request.form['max_heart_rate'] else None
        if 'completion_status' in request.form:
            workout.completion_status = request.form['completion_status']
        if 'difficulty_level' in request.form:
            workout.difficulty_level = request.form['difficulty_level']
        if 'notes' in request.form:
            workout.notes = request.form['notes']
        if 'date' in request.form:
            workout.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        if 'recovery_time' in request.form:
            workout.recovery_time = int(request.form['recovery_time']) if request.form['recovery_time'] else None

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{workout.athlete_id}_{datetime.now().timestamp()}_{file.filename}")
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)
                workout.image_url = f'/static/uploads/workouts/{filename}'

        db.session.commit()

        result = workout.to_dict()
        result['athlete_name'] = workout.athlete.name

        return jsonify({"msg": "Workout updated successfully", "workout": result}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error updating workout: {str(e)}"}), 500

@coach_bp.route("/api/workouts/<int:workout_id>", methods=["DELETE"])
@jwt_required()
def delete_workout(workout_id):
    """Delete a workout"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        workout = (
            db.session.query(WorkoutLog)
            .join(CoachAthlete, CoachAthlete.athlete_id == WorkoutLog.athlete_id)
            .filter(
                WorkoutLog.id == workout_id,
                CoachAthlete.coach_id == identity,
                CoachAthlete.is_active == True
            )
            .first()
        )

        if not workout:
            return jsonify({"msg": "Workout not found"}), 404

        db.session.delete(workout)
        db.session.commit()

        return jsonify({"msg": "Workout deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error deleting workout: {str(e)}"}), 500
