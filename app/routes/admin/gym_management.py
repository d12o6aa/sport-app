# ================================
# Fixed Admin Routes for Gym Management
# ================================

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from app import db
from app.models import Equipment, Event, WorkoutType, User, TrainingPlan, Notification
from . import admin_bp
import json

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/gym_management", methods=["GET"])
@jwt_required()
def gym_management():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    equipments = Equipment.query.all()
    events = Event.query.filter(Event.date >= date.today()).order_by(Event.date).all()
    workout_types = WorkoutType.query.all()
    training_plans = TrainingPlan.query.order_by(TrainingPlan.created_at.desc()).limit(10).all()
    
    return render_template(
        "admin/gym_management.html", 
        equipments=equipments, 
        events=events, 
        workout_types=workout_types, 
        training_plans=training_plans, 
        User=User
    )

# ================================
# Equipment Management APIs (Fixed)
# ================================

@admin_bp.route("/add_equipment", methods=["POST"])
@jwt_required()
def add_equipment():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.form
        equipment = Equipment(
            name=data.get("name"),
            description=data.get("description", ""),
            status=data.get("status", "available"),
            created_at=datetime.utcnow()
        )
        
        db.session.add(equipment)
        db.session.commit()
        
        # Send notification about new equipment
        send_equipment_notification(equipment, 'new')
        
        flash("Equipment added successfully!", "success")
        return redirect(url_for("admin.gym_management"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding equipment: {str(e)}", "danger")
        return redirect(url_for("admin.gym_management"))

@admin_bp.route("/api/equipment/<int:equipment_id>", methods=["PUT"])
@jwt_required()
def update_equipment(equipment_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        equipment = Equipment.query.get_or_404(equipment_id)
        data = request.form
        
        equipment.name = data.get("name", equipment.name)
        equipment.description = data.get("description", equipment.description)
        equipment.status = data.get("status", equipment.status)
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Equipment updated successfully"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/api/equipment/<int:equipment_id>/toggle-status", methods=["POST"])
@jwt_required()
def toggle_equipment_status(equipment_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        equipment = Equipment.query.get_or_404(equipment_id)
        
        # Toggle between available and maintenance
        if equipment.status == "available":
            equipment.status = "maintenance"
        else:
            equipment.status = "available"
        
        db.session.commit()
        
        # Send notification about status change
        send_equipment_notification(equipment, 'status_change')
        
        return jsonify({
            "success": True, 
            "new_status": equipment.status,
            "message": f"Equipment status changed to {equipment.status}"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

# ================================
# Event Management APIs (Fixed)
# ================================

@admin_bp.route("/add_event", methods=["POST"])
@jwt_required()
def add_event():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.form
        event = Event(
            title=data.get("title"),
            description=data.get("description", ""),
            date=datetime.strptime(data.get("date"), "%Y-%m-%d").date(),
            created_at=datetime.utcnow()
        )
        
        # Add optional time if provided
        if data.get("start_time"):
            event.start_time = datetime.strptime(data.get("start_time"), "%H:%M").time()
        
        db.session.add(event)
        db.session.commit()
        
        # Send notifications if requested
        if data.get("notify_members"):
            send_event_notification(event)
            add_event_to_calendars(event)
        
        flash("Event created successfully!", "success")
        return redirect(url_for("admin.gym_management"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating event: {str(e)}", "danger")
        return redirect(url_for("admin.gym_management"))

@admin_bp.route("/api/send-event-notification/<int:event_id>", methods=["POST"])
@jwt_required()
def send_event_notification_api(event_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        event = Event.query.get_or_404(event_id)
        count = send_event_notification(event)
        
        return jsonify({
            "success": True,
            "recipients_count": count,
            "message": f"Notification sent to {count} members"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ================================
# Workout Type Management APIs (Fixed)
# ================================

@admin_bp.route("/add_workout_type", methods=["POST"])
@jwt_required()
def add_workout_type():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.form
        
        # Check if workout type already exists
        existing = WorkoutType.query.filter_by(name=data.get("name")).first()
        if existing:
            flash("Workout type with this name already exists!", "warning")
            return redirect(url_for("admin.gym_management"))
        
        workout_type = WorkoutType(
            name=data.get("name"),
            description=data.get("description", ""),
            created_at=datetime.utcnow()
        )
        
        db.session.add(workout_type)
        db.session.commit()
        
        flash("Workout type added successfully!", "success")
        return redirect(url_for("admin.gym_management"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding workout type: {str(e)}", "danger")
        return redirect(url_for("admin.gym_management"))

@admin_bp.route("/delete_workout_type/<int:id>", methods=["POST"])
@jwt_required()
def delete_workout_type(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        workout_type = WorkoutType.query.get_or_404(id)
        db.session.delete(workout_type)
        db.session.commit()
        
        flash("Workout type deleted successfully!", "success")
        return redirect(url_for("admin.gym_management"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting workout type: {str(e)}", "danger")
        return redirect(url_for("admin.gym_management"))

# ================================
# Training Plan Management APIs (Fixed)
# ================================

@admin_bp.route("/add_workout_plan", methods=["POST"])
@jwt_required()
def add_workout_plan():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            exercises_data = data.get("exercises", [])
        else:
            data = request.form.to_dict()
            exercises_data = []
            
            # Parse exercises from form (if using traditional form submission)
            i = 0
            while f"exercise_name_{i}" in data:
                exercises_data.append({
                    "name": data.get(f"exercise_name_{i}"),
                    "sets": data.get(f"exercise_sets_{i}"),
                    "reps": data.get(f"exercise_reps_{i}")
                })
                i += 1
        
        # Validate required fields
        if not data.get("title") or not data.get("athlete_id"):
            error_msg = "Title and athlete selection are required"
            if request.is_json:
                return jsonify({"success": False, "error": error_msg}), 400
            else:
                flash(error_msg, "warning")
                return redirect(url_for("admin.gym_management"))
        
        # Create exercises dictionary
        exercises_dict = {}
        for i, exercise in enumerate(exercises_data):
            if exercise.get("name"):
                exercises_dict[str(i)] = {
                    "name": exercise["name"],
                    "sets": int(exercise.get("sets", 0)),
                    "reps": int(exercise.get("reps", 0))
                }
        
        # Create training plan
        workout_plan = TrainingPlan(
            athlete_id=int(data.get("athlete_id")),
            coach_id=identity,
            title=data.get("title"),
            description=data.get("description", ""),
            start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d").date(),
            end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d").date(),
            exercises=exercises_dict,
            status="active",
            created_at=datetime.utcnow()
        )
        
        db.session.add(workout_plan)
        db.session.commit()
        
        # Send notification to assigned athlete
        send_training_plan_notification(workout_plan)
        
        success_msg = "Training plan created successfully!"
        if request.is_json:
            return jsonify({"success": True, "plan_id": workout_plan.id, "message": success_msg})
        else:
            flash(success_msg, "success")
            return redirect(url_for("admin.gym_management"))
            
    except ValueError as e:
        db.session.rollback()
        error_msg = f"Invalid data format: {str(e)}"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        else:
            flash(error_msg, "danger")
            return redirect(url_for("admin.gym_management"))
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error creating training plan: {str(e)}"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        else:
            flash(error_msg, "danger")
            return redirect(url_for("admin.gym_management"))

@admin_bp.route("/update_workout_plan/<int:id>", methods=["POST"])
@jwt_required()
def update_workout_plan(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = TrainingPlan.query.get_or_404(id)

        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
            exercises_data = data.get("exercises", [])
        else:
            data = request.form.to_dict()
            exercises_data = []
            i = 0
            while f"exercise_name_{i}" in data:
                exercises_data.append({
                    "name": data.get(f"exercise_name_{i}"),
                    "sets": data.get(f"exercise_sets_{i}"),
                    "reps": data.get(f"exercise_reps_{i}")
                })
                i += 1

        # Update plan fields
        plan.athlete_id = int(data.get("athlete_id", plan.athlete_id))
        plan.title = data.get("title", plan.title)
        plan.description = data.get("description", plan.description)
        plan.workout_type_id = data.get("workout_type_id", plan.workout_type_id)
        plan.start_date = datetime.strptime(data.get("start_date", plan.start_date.isoformat()), "%Y-%m-%d").date()
        plan.end_date = datetime.strptime(data.get("end_date", plan.end_date.isoformat()), "%Y-%m-%d").date()

        # Update exercises
        exercises_dict = {}
        for i, exercise in enumerate(exercises_data):
            if exercise.get("name"):
                exercises_dict[str(i)] = {
                    "name": exercise["name"],
                    "sets": int(exercise.get("sets", 0)),
                    "reps": int(exercise.get("reps", 0))
                }
        plan.exercises = exercises_dict

        db.session.commit()
        send_training_plan_notification(plan)  # Notify athlete about update
        success_msg = "Training plan updated successfully!"
        if request.is_json:
            return jsonify({"success": True, "plan_id": plan.id, "message": success_msg})
        else:
            flash(success_msg, "success")
            return redirect(url_for("admin.gym_management"))

    except ValueError as e:
        db.session.rollback()
        error_msg = f"Invalid data format: {str(e)}"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        else:
            flash(error_msg, "danger")
            return redirect(url_for("admin.gym_management"))
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error updating training plan: {str(e)}"
        if request.is_json:
            return jsonify({"success": False, "error": error_msg}), 400
        else:
            flash(error_msg, "danger")
            return redirect(url_for("admin.gym_management"))

# ================================
# Notification System APIs (Fixed)
# ================================

@admin_bp.route("/api/send-notification", methods=["POST"])
@jwt_required()
def send_notification_api():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        
        notification_type = data.get('type', 'general')
        title = data.get('title')
        message = data.get('message')
        recipients = data.get('recipients', 'all')
        
        if not title or not message:
            return jsonify({"success": False, "error": "Title and message are required"}), 400
        
        # Get target users
        if recipients == 'all':
            users = User.query.filter_by(is_deleted=False).all()
        elif recipients == 'athletes':
            users = User.query.filter_by(role='athlete', is_deleted=False).all()
        elif recipients == 'coaches':
            users = User.query.filter_by(role='coach', is_deleted=False).all()
        else:
            users = User.query.filter_by(is_deleted=False).all()
        
        notifications_created = 0
        
        for user in users:
            if user.id != identity and user.role == 'athlete':  # Only send to athletes
                notification = Notification(
                    coach_id=identity,
                    athlete_id=user.id,
                    title=title,
                    content=message,
                    type=notification_type,
                    priority='medium',
                    sent_at=datetime.utcnow()
                )
                db.session.add(notification)
                notifications_created += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "recipients_count": notifications_created,
            "message": f"Notification sent to {notifications_created} users"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

# ================================
# Helper Functions (Fixed)
# ================================

def send_event_notification(event):
    """Send notification to all users about new event"""
    try:
        athletes = User.query.filter_by(role='athlete', is_deleted=False).all()
        admin_user = User.query.filter_by(role='admin').first()
        
        if not admin_user:
            return 0
        
        notifications_count = 0
        
        for athlete in athletes:
            notification = Notification(
                coach_id=admin_user.id,
                athlete_id=athlete.id,
                title=f"New Event: {event.title}",
                content=f"{event.title} scheduled for {event.date.strftime('%B %d, %Y')}. {event.description}",
                type='event',
                priority='medium',
                sent_at=datetime.utcnow()
            )
            db.session.add(notification)
            notifications_count += 1
        
        db.session.commit()
        return notifications_count
        
    except Exception as e:
        print(f"Error sending event notification: {str(e)}")
        return 0

def send_equipment_notification(equipment, action_type):
    """Send notification about equipment updates"""
    try:
        athletes = User.query.filter_by(role='athlete', is_deleted=False).all()
        admin_user = User.query.filter_by(role='admin').first()
        
        if not admin_user:
            return
        
        if action_type == 'new':
            title = "New Equipment Available"
            message = f"New equipment added: {equipment.name}. {equipment.description}"
        elif action_type == 'status_change':
            status_msg = "available for use" if equipment.status == "available" else "under maintenance"
            title = "Equipment Status Update"
            message = f"{equipment.name} is now {status_msg}."
        else:
            title = "Equipment Update"
            message = f"Equipment notification: {equipment.name}"
        
        for athlete in athletes:
            notification = Notification(
                coach_id=admin_user.id,
                athlete_id=athlete.id,
                title=title,
                content=message,
                type='equipment',
                priority='low',
                sent_at=datetime.utcnow()
            )
            db.session.add(notification)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error sending equipment notification: {str(e)}")

def send_training_plan_notification(plan):
    """Send notification to athlete about new training plan"""
    try:
        if plan.athlete_id:
            admin_user = User.query.filter_by(role='admin').first()
            if admin_user:
                notification = Notification(
                    coach_id=admin_user.id,
                    athlete_id=plan.athlete_id,
                    title="New Training Plan Assigned",
                    content=f"A new training plan '{plan.title}' has been assigned to you. Start date: {plan.start_date}",
                    type='training_plan',
                    priority='high',
                    sent_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.commit()
                
    except Exception as e:
        print(f"Error sending training plan notification: {str(e)}")

def add_event_to_calendars(event):
    """Add event to all users' calendars/schedules"""
    try:
        from app.models import AthleteSchedule
        
        athletes = User.query.filter_by(role='athlete', is_deleted=False).all()
        
        # Calculate event time
        event_start = datetime.combine(event.date, datetime.min.time().replace(hour=10))
        if event.start_time:
            event_start = datetime.combine(event.date, event.start_time)
        
        event_end = datetime.combine(event.date, datetime.min.time().replace(hour=12))
        
        for athlete in athletes:
            schedule_item = AthleteSchedule(
                athlete_id=athlete.id,
                title=event.title,
                description=event.description,
                start_time=event_start,
                end_time=event_end,
                created_at=datetime.utcnow()
            )
            db.session.add(schedule_item)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error adding event to calendars: {str(e)}")

@admin_bp.route("/view_plan/<int:id>", methods=["GET"])
@jwt_required()
def view_plan(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.get_or_404(id)
    athlete_name = User.query.get(plan.athlete_id).name if plan.athlete_id else "Unassigned"
    return jsonify({
        "plan": {
            "id": plan.id,
            "title": plan.title,
            "athlete_name": athlete_name,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "description": plan.description,
            "exercises": [{"name": ex["name"], "sets": ex["sets"], "reps": ex["reps"]} for ex in plan.exercises.values()]
        }
    })

@admin_bp.route("/edit_plan/<int:id>", methods=["GET"])
@jwt_required()
def edit_plan(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = TrainingPlan.query.get_or_404(id)
        athlete = User.query.get(plan.athlete_id) if plan.athlete_id else None
        athlete_name = athlete.name if athlete else "Unassigned"

        # Handle exercises safely
        exercises = plan.exercises or {}
        if not isinstance(exercises, dict):
            exercises = {}
            print(f"Warning: Invalid exercises format for plan {id}, resetting to empty dict")

        exercises_list = [
            {"name": ex.get("name", ""), "sets": ex.get("sets", 0), "reps": ex.get("reps", 0)}
            for ex in exercises.values()
        ]

        return jsonify({
            "plan": {
                "id": plan.id,
                "athlete_id": plan.athlete_id,
                "title": plan.title,
                "description": plan.description or "",
                "workout_type_id": plan.workout_type_id,
                "start_date": plan.start_date.isoformat() if plan.start_date else "",
                "end_date": plan.end_date.isoformat() if plan.end_date else "",
                "exercises": exercises_list
            }
        })
    except Exception as e:
        print(f"Error in edit_plan for id {id}: {str(e)}")
        return jsonify({"success": False, "error": f"Failed to fetch plan: {str(e)}"}), 500


# ================================
# Error Handlers
# ================================

@admin_bp.errorhandler(404)
def not_found(error):
    if request.is_json:
        return jsonify({"success": False, "error": "Resource not found"}), 404
    return render_template('errors/404.html'), 404

@admin_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    if request.is_json:
        return jsonify({"success": False, "error": "Internal server error"}), 500
    return render_template('errors/500.html'), 500