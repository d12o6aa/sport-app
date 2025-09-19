from flask import request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app.extensions import db
from app.models.workout_log import WorkoutLog
from app.models.exercises import Exercise
from app.models.workout_log_exercises import WorkoutLogExercise
import os
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import json

from . import athlete_bp

UPLOAD_FOLDER = 'app/static/uploads/workouts'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================================================
# API Endpoints
# =========================================================

@athlete_bp.route("/api/workouts", methods=["GET"])
@jwt_required()  # Protect this endpoint
def get_workouts():
    try:
        athlete_id = get_jwt_identity()
        
        # Get date range parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        workout_type = request.args.get('type')
        
        query = WorkoutLog.query.filter_by(athlete_id=athlete_id)
        
        if start_date:
            query = query.filter(WorkoutLog.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(WorkoutLog.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        if workout_type:
            query = query.filter(WorkoutLog.workout_type == workout_type)
            
        workouts = query.order_by(WorkoutLog.date.desc(), WorkoutLog.logged_at.desc()).all()
        
        return jsonify([workout.to_dict() for workout in workouts])
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/create", methods=["POST"])
@jwt_required()
def handle_create_workout():
    try:
        athlete_id = get_jwt_identity()
        
        # Handle file upload (if needed)
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{athlete_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_url = f"/static/uploads/workouts/{filename}"
        
        data = request.form
        
        new_workout = WorkoutLog(
            athlete_id=athlete_id,
            title=data.get("title", "New Custom Workout"),
            workout_type=data.get("workout_type", "strength"),
            difficulty_level=data.get("difficulty_level", "beginner"),
            actual_duration=int(data.get("duration", 0)),
            calories_burned=int(data.get("calories", 0)),
            notes=data.get("notes"),
            image_url=image_url,
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
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/<int:workout_id>", methods=["PUT"])
@jwt_required()
def update_workout(workout_id):
    try:
        athlete_id = get_jwt_identity()
        
        workout = WorkoutLog.query.filter_by(id=workout_id, athlete_id=athlete_id).first_or_404()
        data = request.form
        
        # Update fields
        for field in ['title', 'workout_type', 'session_type', 'feedback', 'notes', 
                     'completion_status', 'difficulty_level']:
            if data.get(field):
                setattr(workout, field, data.get(field))
        
        # Update numeric fields
        for field in ['planned_duration', 'actual_duration', 'total_time', 'calories_burned', 
                     'avg_heart_rate', 'max_heart_rate', 'recovery_time']:
            if data.get(field):
                setattr(workout, field, int(data.get(field)))
        
        # Update JSON fields
        for field in ['hr_zones', 'training_effects', 'workout_details', 'metrics', 'heart_rate_data']:
            if data.get(field):
                setattr(workout, field.replace('_', '-'), json.loads(data.get(field))) # Assuming model has fields like workout_details, not workout-details
        
        # Handle file upload
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
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/workouts/stats", methods=["GET"])
@jwt_required()
def get_workout_stats():
    try:
        athlete_id = get_jwt_identity()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        if request.args.get('start_date'):
            start_date = datetime.strptime(request.args.get('start_date'), '%Y-%m-%d').date()
        if request.args.get('end_date'):
            end_date = datetime.strptime(request.args.get('end_date'), '%Y-%m-%d').date()
        
        workouts = WorkoutLog.query.filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= start_date,
            WorkoutLog.date <= end_date,
            WorkoutLog.completion_status == 'completed'
        ).all()
        
        total_workouts = len(workouts)
        total_time = sum(w.actual_duration or 0 for w in workouts)
        total_calories = sum(w.calories_burned or 0 for w in workouts)
        avg_heart_rate = sum(w.avg_heart_rate or 0 for w in workouts if w.avg_heart_rate) / max(1, len([w for w in workouts if w.avg_heart_rate]))
        
        type_breakdown = {}
        for workout in workouts:
            wtype = workout.workout_type
            if wtype not in type_breakdown:
                type_breakdown[wtype] = {"count": 0, "time": 0, "calories": 0}
            type_breakdown[wtype]["count"] += 1
            type_breakdown[wtype]["time"] += workout.actual_duration or 0
            type_breakdown[wtype]["calories"] += workout.calories_burned or 0
        
        recent_workouts = WorkoutLog.query.filter_by(
            athlete_id=athlete_id
        ).order_by(WorkoutLog.date.desc()).limit(7).all()
        
        return jsonify({
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_workouts": total_workouts,
                "total_time_minutes": total_time,
                "total_calories": total_calories,
                "avg_heart_rate": round(avg_heart_rate) if avg_heart_rate else 0
            },
            "type_breakdown": type_breakdown,
            "recent_workouts": [w.to_dict() for w in recent_workouts]
        })
        
    except Exception as e:
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
        
        workouts = query.order_by(WorkoutLog.date.desc()).all()
        return jsonify([w.to_dict() for w in workouts])
        
    except Exception as e:
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
            workouts = query.order_by(WorkoutLog.date.desc()).limit(10).all()
            
        return jsonify([w.to_dict() for w in workouts])
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

@athlete_bp.route("/api/exercises", methods=["GET"])
@jwt_required()
def get_exercises():
    try:
        body_part = request.args.get('body_part')
        if not body_part:
            return jsonify({"msg": "Missing body part parameter"}), 400
        
        exercises = Exercise.query.filter(Exercise.body_parts.ilike(f'%{body_part}%')).all()
        
        return jsonify([ex.to_dict() for ex in exercises])
        
    except Exception as e:
        return jsonify({"msg": str(e)}), 400

# =========================================================
# View Routes (Renders HTML Pages)
# =========================================================

@athlete_bp.route("/workout/filter")
@jwt_required()
def workout_filter_page():
    return render_template("athlete/workout/filter.html")

@athlete_bp.route("/workout/top-filter")
@jwt_required()
def workout_top_filter_page():
    return render_template("athlete/workout/top_filter.html")

@athlete_bp.route("/workout/body-workout")
@jwt_required()
def body_workout_page():
    return render_template("athlete/workout/body_workout.html")

@athlete_bp.route("/workout/create")
@jwt_required()
def create_workout_page():
    return render_template("athlete/workout/create_workout.html")

@athlete_bp.route("/workout/summary")
@jwt_required()
def workout_summary_page():
    # This route would show a summary of a specific workout or overall stats
    return render_template("athlete/workout/summary.html")