# app/routes/admin/admin.py

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, func
from datetime import datetime, date, time
from app import db
from app.models import (
    Equipment, Event, WorkoutType, User, SessionSchedule,
    EquipmentReservation, CoachAthlete, TrainingPlan
)
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

    # Stats for the cards
    equipments = Equipment.query.all()
    upcoming_events = Event.query.filter(Event.date >= date.today()).order_by(Event.date).all()
    workout_types = WorkoutType.query.all()
    upcoming_sessions = SessionSchedule.query.filter(SessionSchedule.scheduled_at >= datetime.utcnow()).count()
    
    # Data for the modals and lists
    coaches = User.query.filter_by(role="coach", is_deleted=False).all()
    athletes = User.query.filter_by(role="athlete", is_deleted=False).all()
    all_sessions = SessionSchedule.query.order_by(SessionSchedule.scheduled_at.desc()).all()

    return render_template(
        "admin/gym_management.html",
        equipments=equipments,
        events=upcoming_events,
        workout_types=workout_types,
        sessions_count=upcoming_sessions,
        all_sessions=all_sessions,
        coaches=coaches,
        athletes=athletes
    )

# ================================
# Equipment Management APIs
# ================================

@admin_bp.route("/api/equipment/<int:equipment_id>", methods=["GET"])
@jwt_required()
def get_equipment(equipment_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    equipment = Equipment.query.get_or_404(equipment_id)
    return jsonify({
        "success": True,
        "equipment": {
            "id": equipment.id,
            "name": equipment.name,
            "description": equipment.description,
            "status": equipment.status,
            "equipment_type": equipment.equipment_type,
            "maintenance_notes": equipment.maintenance_notes
        }
    })

@admin_bp.route("/add_equipment", methods=["POST"])
@jwt_required()
def add_equipment():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        data = request.get_json()
        equipment = Equipment(
            name=data.get("name"),
            description=data.get("description", ""),
            status=data.get("status", "available"),
            equipment_type=data.get("equipment_type", ""),
            maintenance_notes=data.get("maintenance_notes", ""),
            created_at=datetime.utcnow()
        )
        db.session.add(equipment)
        db.session.commit()
        return jsonify({"success": True, "message": "Equipment added successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/api/equipment/<int:equipment_id>", methods=["PUT"])
@jwt_required()
def update_equipment(equipment_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        equipment = Equipment.query.get_or_404(equipment_id)
        data = request.get_json()
        
        equipment.name = data.get("name", equipment.name)
        equipment.description = data.get("description", equipment.description)
        equipment.status = data.get("status", equipment.status)
        equipment.equipment_type = data.get("equipment_type", equipment.equipment_type)
        equipment.maintenance_notes = data.get("maintenance_notes", equipment.maintenance_notes)
        
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
        if equipment.status == "available":
            equipment.status = "maintenance"
        else:
            equipment.status = "available"
        
        db.session.commit()
        return jsonify({
            "success": True, 
            "new_status": equipment.status,
            "message": f"Equipment status changed to {equipment.status}"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

# ================================
# Event Management APIs
# ================================

@admin_bp.route("/add_event", methods=["POST"])
@jwt_required()
def add_event():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        event = Event(
            title=data.get("title"),
            description=data.get("description", ""),
            date=datetime.strptime(data.get("date"), "%Y-%m-%d").date(),
            created_at=datetime.utcnow()
        )
        if data.get("start_time"):
            event.start_time = datetime.strptime(data.get("start_time"), "%H:%M").time()
        
        db.session.add(event)
        db.session.commit()
        return jsonify({"success": True, "message": "Event created successfully!", "event_id": event.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
        
@admin_bp.route("/delete_event/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_event(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        event = Event.query.get_or_404(id)
        db.session.delete(event)
        db.session.commit()
        return jsonify({"success": True, "message": "Event deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400


# ================================
# Workout Type Management APIs
# ================================

@admin_bp.route("/add_workout_type", methods=["POST"])
@jwt_required()
def add_workout_type():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        existing = WorkoutType.query.filter_by(name=data.get("name")).first()
        if existing:
            return jsonify({"success": False, "error": "Workout type with this name already exists!"}), 409
        
        workout_type = WorkoutType(
            name=data.get("name"),
            description=data.get("description", ""),
            created_at=datetime.utcnow()
        )
        db.session.add(workout_type)
        db.session.commit()
        return jsonify({"success": True, "message": "Workout type added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/delete_workout_type/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_workout_type(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        workout_type = WorkoutType.query.get_or_404(id)
        db.session.delete(workout_type)
        db.session.commit()
        return jsonify({"success": True, "message": "Workout type deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/api/workout_type/<int:id>", methods=["GET"])
@jwt_required()
def get_workout_type(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    workout_type = WorkoutType.query.get_or_404(id)
    return jsonify({
        "success": True,
        "workout_type": {
            "id": workout_type.id,
            "name": workout_type.name,
            "description": workout_type.description
        }
    })

@admin_bp.route("/api/workout_type/<int:id>", methods=["PUT"])
@jwt_required()
def update_workout_type(id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        workout_type = WorkoutType.query.get_or_404(id)
        data = request.get_json()
        workout_type.name = data.get("name", workout_type.name)
        workout_type.description = data.get("description", workout_type.description)
        db.session.commit()
        return jsonify({"success": True, "message": "Workout type updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

# ================================
# Session & Booking APIs
# ================================

@admin_bp.route("/api/sessions", methods=["GET"])
@jwt_required()
def get_all_sessions():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    sessions = SessionSchedule.query.order_by(SessionSchedule.scheduled_at.desc()).all()
    sessions_data = [
        {
            "id": s.id,
            "title": s.title,
            "coach_name": s.coach.name if s.coach else 'N/A',
            "athlete_name": s.athlete.name if s.athlete else 'N/A',
            "scheduled_at": s.scheduled_at.isoformat(),
            "duration": s.duration,
            "status": s.status,
            "type": s.type
        } for s in sessions
    ]
    return jsonify({"success": True, "sessions": sessions_data})

@admin_bp.route("/api/sessions/<int:session_id>", methods=["GET"])
@jwt_required()
def get_session_details(session_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    session = SessionSchedule.query.get_or_404(session_id)
    return jsonify({
        "success": True,
        "session": {
            "id": session.id,
            "title": session.title,
            "coach_id": session.coach_id,
            "athlete_id": session.athlete_id,
            "scheduled_at": session.scheduled_at.isoformat(),
            "duration": session.duration,
            "type": session.type,
            "location": session.location,
            "meeting_link": session.meeting_link,
            "status": session.status
        }
    })

@admin_bp.route("/api/sessions/add", methods=["POST"])
@jwt_required()
def add_session():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        scheduled_at = datetime.fromisoformat(data.get("scheduled_at"))
        
        session = SessionSchedule(
            title=data.get("title"),
            coach_id=data.get("coach_id"),
            athlete_id=data.get("athlete_id"),
            scheduled_at=scheduled_at,
            duration=data.get("duration"),
            type=data.get("type"),
            location=data.get("location"),
            meeting_link=data.get("meeting_link")
        )
        db.session.add(session)
        db.session.commit()
        return jsonify({"success": True, "message": "Session added successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/api/sessions/<int:session_id>", methods=["PUT"])
@jwt_required()
def update_session(session_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        session = SessionSchedule.query.get_or_404(session_id)
        data = request.get_json()
        
        session.title = data.get("title", session.title)
        session.coach_id = data.get("coach_id", session.coach_id)
        session.athlete_id = data.get("athlete_id", session.athlete_id)
        session.scheduled_at = datetime.fromisoformat(data.get("scheduled_at")) if data.get("scheduled_at") else session.scheduled_at
        session.duration = data.get("duration", session.duration)
        session.type = data.get("type", session.type)
        session.location = data.get("location", session.location)
        session.meeting_link = data.get("meeting_link", session.meeting_link)
        session.status = data.get("status", session.status)
        
        db.session.commit()
        return jsonify({"success": True, "message": "Session updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route("/api/sessions/<int:session_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_session(session_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        session = SessionSchedule.query.get_or_404(session_id)
        session.status = 'cancelled'
        db.session.commit()
        return jsonify({"success": True, "message": "Session cancelled successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400