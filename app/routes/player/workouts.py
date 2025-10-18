from flask import Blueprint, request, jsonify, render_template, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import WorkoutLog, AthleteProgress, Exercise, User
from sqlalchemy import desc, func, and_, or_,cast, String
from datetime import datetime, date, timedelta
import os
from werkzeug.utils import secure_filename
import json
import traceback

from . import athlete_bp

UPLOAD_FOLDER = 'app/static/uploads/workouts'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================================================
# View Routes (Renders HTML Pages)
# =========================================================

@athlete_bp.route("/workouts")
@jwt_required()
def workout_hub_page():
    return render_template("athlete/workout_hub.html")

# =========================================================
# API Endpoints for Data Fetching and Management
# =========================================================

@athlete_bp.route("/api/workouts", methods=["GET"])
@jwt_required()
def get_workouts():
    try:
        athlete_id = get_jwt_identity()
        workouts = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(desc(WorkoutLog.date), desc(WorkoutLog.logged_at)).all()
        return jsonify([workout.to_dict() for workout in workouts])
    except Exception as e:
        print(f"Error in get_workouts: {e}")
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/create", methods=["POST"])
@jwt_required()
def handle_create_workout():
    try:
        athlete_id = get_jwt_identity()
        
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_url = f"/static/uploads/workouts/{filename}"
        
        data = request.form
        
        workout_type_value = data.get('workout_type', 'other')
        custom_workout_type = data.get('custom_workout_type', None)
        final_workout_type = custom_workout_type if workout_type_value == 'other' and custom_workout_type else workout_type_value

        new_workout = WorkoutLog(
            athlete_id=athlete_id,
            title=data.get("title", "New Custom Workout"),
            workout_type=final_workout_type,
            session_type="workout",
            difficulty_level=data.get("difficulty_level", "beginner"),
            planned_duration=int(data.get("planned_duration", 0)),
            actual_duration=int(data.get("actual_duration", 0)),
            calories_burned=int(data.get("calories_burned", 0)),
            avg_heart_rate=int(data.get("avg_heart_rate", 0)) if data.get("avg_heart_rate") else None,
            max_heart_rate=int(data.get("max_heart_rate", 0)) if data.get("max_heart_rate") else None,
            recovery_time=int(data.get("recovery_time", 0)) if data.get("recovery_time") else None,
            notes=data.get("notes"),
            image_url=image_url,
            completion_status=data.get("completion_status", "completed"),
            date=datetime.strptime(data.get("date"), '%Y-%m-%d').date() if data.get("date") else date.today()
        )
        
        db.session.add(new_workout)
        db.session.commit()
        
        return jsonify({
            "msg": "Workout created successfully!", 
            "id": new_workout.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating workout: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/<int:workout_id>", methods=["PUT"])
@jwt_required()
def update_workout(workout_id):
    try:
        athlete_id = get_jwt_identity()
        workout = WorkoutLog.query.filter_by(id=workout_id, athlete_id=athlete_id).first_or_404()
        
        data = request.form
        
        workout_type_value = data.get('workout_type', 'other')
        custom_workout_type = data.get('custom_workout_type', None)
        final_workout_type = custom_workout_type if workout_type_value == 'other' and custom_workout_type else workout_type_value

        for field in ['title', 'notes', 'completion_status', 'difficulty_level']:
            if data.get(field):
                setattr(workout, field, data.get(field))
        
        workout.workout_type = final_workout_type
        workout.planned_duration = int(data.get('planned_duration')) if data.get('planned_duration') else workout.planned_duration
        workout.actual_duration = int(data.get('actual_duration')) if data.get('actual_duration') else workout.actual_duration
        workout.calories_burned = int(data.get('calories_burned')) if data.get('calories_burned') else workout.calories_burned
        workout.avg_heart_rate = int(data.get('avg_heart_rate')) if data.get('avg_heart_rate') else workout.avg_heart_rate
        workout.max_heart_rate = int(data.get('max_heart_rate')) if data.get('max_heart_rate') else workout.max_heart_rate
        workout.recovery_time = int(data.get('recovery_time')) if data.get('recovery_time') else workout.recovery_time

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                workout.image_url = f"/static/uploads/workouts/{filename}"
        
        db.session.commit()
        return jsonify({
            "msg": "Workout updated successfully!",
            "workout": workout.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating workout: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/<int:workout_id>", methods=["DELETE"])
@jwt_required()
def delete_workout(workout_id):
    try:
        athlete_id = get_jwt_identity()
        workout = WorkoutLog.query.filter_by(id=workout_id, athlete_id=athlete_id).first_or_404()
        db.session.delete(workout)
        db.session.commit()
        return jsonify({"msg": "Workout deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting workout: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400
        
@athlete_bp.route("/api/progress", methods=["GET"])
@jwt_required()
def get_progress_data():
    try:
        athlete_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        workouts_data = WorkoutLog.query.filter_by(athlete_id=athlete_id).filter(
            WorkoutLog.date >= start_date.date()
        ).order_by(WorkoutLog.date).all()
        
        progress_data = AthleteProgress.query.filter_by(athlete_id=athlete_id).filter(
            AthleteProgress.date >= start_date.date()
        ).order_by(AthleteProgress.date).all()
        
        dates = sorted(list(set([w.date.isoformat() for w in workouts_data] + [p.date.isoformat() for p in progress_data])))
        
        workout_map = {w.date.isoformat(): w for w in workouts_data}
        progress_map = {p.date.isoformat(): p for p in progress_data}
        
        calories_burned = [workout_map.get(d).calories_burned or 0 for d in dates if d in workout_map]
        weights = [progress_map.get(d).weight or 0 for d in dates if d in progress_map]
        
        return jsonify({
            "labels": dates,
            "calories_burned": calories_burned,
            "weights": weights
        })

    except Exception as e:
        print(f"Error in get_progress_data: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400


@athlete_bp.route("/api/workouts/progress", methods=["GET"])
@jwt_required()
def get_workouts_progress_data():
    """Get progress data for workout charts (calories/weight over time)"""
    try:
        athlete_id = get_jwt_identity()
        days = request.args.get('days', 30, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        workouts_data = WorkoutLog.query.filter_by(athlete_id=athlete_id).filter(
            WorkoutLog.date >= start_date.date()
        ).order_by(WorkoutLog.date).all()
        
        progress_data = AthleteProgress.query.filter_by(athlete_id=athlete_id).filter(
            AthleteProgress.date >= start_date.date()
        ).order_by(AthleteProgress.date).all()
        
        dates = sorted(list(set([w.date.isoformat() for w in workouts_data] + [p.date.isoformat() for p in progress_data])))
        
        workout_map = {w.date.isoformat(): w for w in workouts_data}
        progress_map = {p.date.isoformat(): p for p in progress_data}
        
        calories_burned = [workout_map.get(d).calories_burned or 0 for d in dates if d in workout_map]
        weights = [progress_map.get(d).weight or 0 for d in dates if d in progress_map]
        
        return jsonify({
            "labels": dates,
            "calories_burned": calories_burned,
            "weights": weights
        }), 200

    except Exception as e:
        print(f"Error in get_workouts_progress_data: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/filter", methods=["POST"])
@jwt_required()
def filter_workouts_api():
    try:
        athlete_id = get_jwt_identity()
        filters = request.get_json()
        
        query = WorkoutLog.query.filter_by(athlete_id=athlete_id)
        
        if filters.get('type'):
            query = query.filter(WorkoutLog.workout_type == filters['type'])
        if filters.get('difficulty'):
            query = query.filter(WorkoutLog.difficulty_level == filters['difficulty'])
        if filters.get('status'):
            query = query.filter(WorkoutLog.completion_status == filters['status'])
        if filters.get('duration'):
            duration_range = filters['duration']
            if '-' in duration_range:
                min_dur, max_dur = map(int, duration_range.split('-'))
                query = query.filter(
                    WorkoutLog.actual_duration >= min_dur,
                    WorkoutLog.actual_duration <= max_dur
                )
            elif duration_range == '60+':
                query = query.filter(WorkoutLog.actual_duration >= 60)
        
        workouts = query.order_by(desc(WorkoutLog.date)).all()
        return jsonify([w.to_dict() for w in workouts])
        
    except Exception as e:
        print(f"Error in filter_workouts_api: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/top", methods=["GET"])
@jwt_required()
def get_top_workouts_api():
    try:
        athlete_id = get_jwt_identity()
        sort_by = request.args.get('sort', 'calories')
        
        query = WorkoutLog.query.filter_by(
            athlete_id=athlete_id, 
            completion_status='completed'
        )
        
        if sort_by == 'calories':
            workouts = query.order_by(WorkoutLog.calories_burned.desc()).limit(10).all()
        elif sort_by == 'duration':
            workouts = query.order_by(WorkoutLog.actual_duration.desc()).limit(10).all()
        else:  # recent
            workouts = query.order_by(desc(WorkoutLog.date)).limit(10).all()
            
        return jsonify([w.to_dict() for w in workouts])
        
    except Exception as e:
        print(f"Error in get_top_workouts_api: {traceback.format_exc()}")
        return jsonify({"msg": str(e)}), 400
@athlete_bp.route("/api/exercises", methods=["GET"])
@jwt_required()
def get_exercises():
    try:
        body_parts_str = request.args.get('body_part')
        if not body_parts_str:
            return jsonify({"msg": "Missing body part parameter"}), 400
        
        body_parts = [part.strip().lower() for part in body_parts_str.split(',')]
        
        # Option 1: Using PostgreSQL's ?| operator correctly with text casting
        # The ?| operator checks if any of the strings in an array exist as top-level keys
        # We need to cast muscle_groups to text and use LIKE for flexible matching
        
        query = db.session.query(Exercise).filter(Exercise.is_active == True)
        
        # Build OR conditions for each body part
        conditions = []
        for body_part in body_parts:
            # Cast JSON to text and use ILIKE for case-insensitive search
            conditions.append(
                cast(Exercise.muscle_groups, String).ilike(f'%{body_part}%')
            )
        
        if conditions:
            query = query.filter(or_(*conditions))
        
        exercises = query.all()
        
        return jsonify([ex.to_dict() for ex in exercises])
        
    except Exception as e:
        print(f"Error in get_exercises: {traceback.format_exc()}")
        return jsonify({"msg": "An error occurred while fetching exercises."}), 400


# Alternative implementation if you need more precise JSON array matching:
@athlete_bp.route("/api/exercises/precise", methods=["GET"])
@jwt_required()
def get_exercises_precise():
    """
    Alternative implementation using PostgreSQL's jsonb_array_elements
    This is more precise but requires jsonb column type
    """
    try:
        body_parts_str = request.args.get('body_part')
        if not body_parts_str:
            return jsonify({"msg": "Missing body part parameter"}), 400
        
        body_parts = [part.strip().lower() for part in body_parts_str.split(',')]
        
        # Use raw SQL for complex JSON operations
        from sqlalchemy import text
        
        placeholders = ', '.join([f':body_part_{i}' for i in range(len(body_parts))])
        
        sql = text(f"""
            SELECT DISTINCT e.*
            FROM exercises e,
                 jsonb_array_elements_text(e.muscle_groups) AS muscle_group
            WHERE LOWER(muscle_group) IN ({placeholders})
              AND e.is_active = true
        """)
        
        # Create parameter dict
        params = {f'body_part_{i}': body_part for i, body_part in enumerate(body_parts)}
        
        result = db.session.execute(sql, params)
        exercises = result.fetchall()
        
        # Convert to dict manually since we used raw SQL
        exercises_list = []
        for row in exercises:
            exercise = Exercise.query.get(row.id)
            if exercise:
                exercises_list.append(exercise.to_dict())
        
        return jsonify(exercises_list)
        
    except Exception as e:
        print(f"Error in get_exercises_precise: {traceback.format_exc()}")
        return jsonify({"msg": "An error occurred while fetching exercises."}), 400
