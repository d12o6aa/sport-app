# In coach_bp.py

from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, SessionSchedule, Notification
from sqlalchemy import or_, and_
from sqlalchemy.sql import func

from . import coach_bp

# Helper function
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"


@coach_bp.route("/sessions", methods=["GET"])
@jwt_required()
def coach_sessions_page():
    """Render coach sessions management page"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    return render_template("coach/sessions.html")


@coach_bp.route("/api/sessions", methods=["GET"])
@jwt_required()
def get_coach_sessions():
    """Get all sessions for the coach (pending, approved, rejected)"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    # Get all sessions where this user is the coach
    sessions = SessionSchedule.query.filter_by(coach_id=identity).all()
    
    events = []
    for s in sessions:
        athlete = User.query.get(s.athlete_id)
        
        # Determine color based on status
        if s.status == "pending":
            color = "#ffc107"  # Warning yellow
        elif s.status == "scheduled":
            color = "#198754"  # Success green
        elif s.status == "rejected":
            color = "#dc3545"  # Danger red
        else:
            color = "#0d6efd"  # Primary blue
        
        events.append({
            "id": s.id,
            "title": s.title,
            "athlete_id": s.athlete_id,
            "athlete_name": athlete.name if athlete else "Unknown",
            "start": s.scheduled_at.isoformat(),
            "end": s.end_time.isoformat(),
            "duration": s.duration,
            "type": s.type,
            "status": s.status,
            "color": color,
            "location": s.location,
            "meeting_link": s.meeting_link,
            "rejection_reason": getattr(s, 'rejection_reason', None),
            "created_at": s.scheduled_at.isoformat()  # Using scheduled_at as proxy
        })
    
    return jsonify(events)


@coach_bp.route("/api/sessions/<int:session_id>/approve", methods=["POST"])
@jwt_required()
def approve_session(session_id):
    """Approve a pending session request"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    session = SessionSchedule.query.get(session_id)
    
    if not session:
        return jsonify({"msg": "Session not found"}), 404
    
    if session.coach_id != identity:
        return jsonify({"msg": "Unauthorized - Not your session"}), 403
    
    if session.status != "pending":
        return jsonify({"msg": "Session is not pending"}), 400
    
    # Check for overlapping sessions
    scheduled_end = session.scheduled_at + timedelta(minutes=session.duration)
    
    overlapping_session = SessionSchedule.query.filter(
        SessionSchedule.coach_id == identity,
        SessionSchedule.id != session_id,
        SessionSchedule.status.in_(["scheduled", "in_progress"]),
        and_(
            SessionSchedule.scheduled_at < scheduled_end,
            (SessionSchedule.scheduled_at + func.make_interval(0, 0, 0, 0, 0, SessionSchedule.duration)) > session.scheduled_at
        )
    ).first()
    
    if overlapping_session:
        return jsonify({
            "msg": "Time slot conflicts with another approved session",
            "success": False
        }), 409
    
    # Approve the session
    session.status = "scheduled"
    db.session.commit()
    
    # Send notification to athlete
    athlete = User.query.get(session.athlete_id)
    coach = User.query.get(identity)
    
    notification = Notification(
        coach_id=identity,
        athlete_id=session.athlete_id,
        title="Session Approved! 🎉",
        content=f"Your session '{session.title}' on {session.scheduled_at.strftime('%B %d at %H:%M')} has been approved by Coach {coach.name if coach else 'your coach'}.",
        type="event",
        priority="high",
        action_url=f"/athlete/sessions/{session.id}"
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        "msg": "Session approved successfully!",
        "success": True,
        "session_id": session.id
    }), 200


@coach_bp.route("/api/sessions/<int:session_id>/reject", methods=["POST"])
@jwt_required()
def reject_session(session_id):
    """Reject a pending session request with reason"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    data = request.get_json()
    reason = data.get("reason", "").strip()
    
    if not reason:
        return jsonify({"msg": "Rejection reason is required"}), 400
    
    session = SessionSchedule.query.get(session_id)
    
    if not session:
        return jsonify({"msg": "Session not found"}), 404
    
    if session.coach_id != identity:
        return jsonify({"msg": "Unauthorized - Not your session"}), 403
    
    if session.status != "pending":
        return jsonify({"msg": "Session is not pending"}), 400
    
    # Reject the session
    session.status = "rejected"
    
    # Store rejection reason (you may need to add this field to your model)
    # For now, we'll store it in a notification
    db.session.commit()
    
    # Send notification to athlete
    athlete = User.query.get(session.athlete_id)
    coach = User.query.get(identity)
    
    notification = Notification(
        coach_id=identity,
        athlete_id=session.athlete_id,
        title="Session Request Declined",
        content=f"Your session request '{session.title}' on {session.scheduled_at.strftime('%B %d at %H:%M')} was declined. Reason: {reason}",
        type="alert",
        priority="high",
        action_url="/athlete/book_sessions",
        extra_data={"rejection_reason": reason, "session_id": session.id}
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        "msg": "Session rejected successfully!",
        "success": True
    }), 200


@coach_bp.route("/api/sessions/<int:session_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_session(session_id):
    """Cancel an approved session"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    data = request.get_json()
    reason = data.get("reason", "").strip()
    
    session = SessionSchedule.query.get(session_id)
    
    if not session:
        return jsonify({"msg": "Session not found"}), 404
    
    if session.coach_id != identity:
        return jsonify({"msg": "Unauthorized - Not your session"}), 403
    
    if session.status == "cancelled":
        return jsonify({"msg": "Session is already cancelled"}), 400
    
    # Cancel the session
    session.status = "cancelled"
    db.session.commit()
    
    # Notify athlete
    notification = Notification(
        coach_id=identity,
        athlete_id=session.athlete_id,
        title="Session Cancelled",
        content=f"Session '{session.title}' on {session.scheduled_at.strftime('%B %d at %H:%M')} has been cancelled. {reason}",
        type="alert",
        priority="high"
    )
    db.session.add(notification)
    db.session.commit()
    
    return jsonify({
        "msg": "Session cancelled successfully!",
        "success": True
    }), 200


@coach_bp.route("/api/stats", methods=["GET"])
@jwt_required()
def get_coach_stats():
    """Get coach statistics"""
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    # Count sessions by status
    pending = SessionSchedule.query.filter_by(
        coach_id=identity, 
        status="pending"
    ).count()
    
    scheduled = SessionSchedule.query.filter_by(
        coach_id=identity, 
        status="scheduled"
    ).count()
    
    # Count active athletes
    active_athletes = db.session.query(CoachAthlete).filter(
        CoachAthlete.coach_id == identity,
        CoachAthlete.is_active == True
    ).count()
    
    # Today's sessions
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    today_sessions = SessionSchedule.query.filter(
        SessionSchedule.coach_id == identity,
        SessionSchedule.status == "scheduled",
        SessionSchedule.scheduled_at >= today_start,
        SessionSchedule.scheduled_at < today_end
    ).count()
    
    return jsonify({
        "pending": pending,
        "scheduled": scheduled,
        "active_athletes": active_athletes,
        "today_sessions": today_sessions
    })