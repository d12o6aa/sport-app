# In athlete_bp.py

from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, SessionSchedule, Notification
from sqlalchemy import or_, and_
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import INTERVAL

from . import athlete_bp

# ... (is_athlete function)
def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.role == "athlete"

@athlete_bp.route("/book_sessions", methods=["GET"])
@jwt_required()
def book_sessions_page():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    coaches = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.coach_id == User.id)
        .filter(CoachAthlete.athlete_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("athlete/book_sessions.html", coaches=coaches)

@athlete_bp.route("/api/sessions", methods=["GET"])
@jwt_required()
def get_sessions():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user:
        return jsonify({"msg": "Unauthorized"}), 403
    
    coaches_ids = [c.coach_id for c in user.coach_links.all()]
    
    all_sessions = SessionSchedule.query.filter(
        or_(
            SessionSchedule.athlete_id == identity,
            SessionSchedule.coach_id.in_(coaches_ids)
        )
    ).all()
    
    events = []
    for s in all_sessions:
        if s.athlete_id == identity:
            color = "#0d6efd"
        else:
            color = "#ffc107"

        events.append({
            "id": s.id,
            "title": s.title,
            "start": s.scheduled_at.isoformat(),
            "end": s.end_time.isoformat(),
            "color": color,
            "is_athlete_session": s.athlete_id == identity,
            "coach_id": s.coach_id
        })
        
    return jsonify(events)

@athlete_bp.route("/api/sessions", methods=["POST"])
@jwt_required()
def book_session_api():
    identity = get_jwt_identity()
    data = request.get_json()
    
    coach_id = data.get("coach_id")
    title = data.get("title")
    duration = data.get("duration")
    scheduled_at_str = data.get("scheduled_at")
    
    if not all([coach_id, title, duration, scheduled_at_str]):
        return jsonify({"msg": "Missing required fields"}), 400
    
    try:
        scheduled_at = datetime.strptime(scheduled_at_str, "%Y-%m-%dT%H:%M")
        scheduled_end = scheduled_at + timedelta(minutes=duration)
    except ValueError:
        return jsonify({"msg": "Invalid date format"}), 400

    link = CoachAthlete.query.filter_by(coach_id=coach_id, athlete_id=identity, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not linked to this coach"}), 403

    overlapping_session = SessionSchedule.query.filter(
        SessionSchedule.coach_id == coach_id,
        SessionSchedule.status.in_(["scheduled", "in_progress"]),
        and_(
            SessionSchedule.scheduled_at < scheduled_end,
            (SessionSchedule.scheduled_at + func.make_interval(0, 0, 0, 0, 0, SessionSchedule.duration)) > scheduled_at
        )
    ).first()

    if overlapping_session:
        return jsonify({"msg": "This time slot is already booked with this coach."}), 409

    session = SessionSchedule(
        coach_id=coach_id,
        athlete_id=identity,
        title=title,
        duration=duration,
        scheduled_at=scheduled_at,
        status="scheduled"
    )
    db.session.add(session)
    db.session.commit()

    # 4. Corrected Notification creation
    notification = Notification(
        coach_id=coach_id,
        athlete_id=identity,
        content=f"New session booked by {User.query.get(identity).name} on {scheduled_at.strftime('%Y-%m-%d at %H:%M')}.",
        type="new_session"
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({"msg": "Session booked successfully!", "id": session.id}), 201