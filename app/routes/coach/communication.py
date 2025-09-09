from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, Notification, SessionSchedule

communication_bp = Blueprint('communication', __name__, url_prefix='/coach')

# Helper function to check if user is a coach
def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# Communication dashboard
@communication_bp.route("/communication", methods=["GET"])
@jwt_required()
def communication():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )
    return render_template("coach/communication.html", athletes=athletes)

# Send notification or video
@communication_bp.route("/athlete/<int:athlete_id>/send_notification", methods=["POST"])
@jwt_required()
def send_notification(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.form
    content = data.get("content")
    notification_type = data.get("type")  # message, video, alert
    file_path = data.get("file_path")  # For videos

    if not content or not notification_type:
        return jsonify({"msg": "Missing required fields"}), 400

    try:
        notification = Notification(
            coach_id=identity,
            athlete_id=athlete_id,
            content=content,
            type=notification_type,
            file_path=file_path,
            sent_at=datetime.utcnow(),
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()
        flash("Notification sent successfully!", "success")
        return redirect(url_for("communication.communication"))
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Schedule session
@communication_bp.route("/athlete/<int:athlete_id>/schedule_session", methods=["POST"])
@jwt_required()
def schedule_session(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id, is_active=True).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.form
    title = data.get("title")
    session_type = data.get("type")  # virtual, in_person
    scheduled_at = data.get("scheduled_at")
    duration = data.get("duration")
    location = data.get("location")
    meeting_link = data.get("meeting_link")

    if not title or not session_type or not scheduled_at:
        return jsonify({"msg": "Missing required fields"}), 400

    try:
        session = SessionSchedule(
            coach_id=identity,
            athlete_id=athlete_id,
            title=title,
            type=session_type,
            scheduled_at=datetime.strptime(scheduled_at, "%Y-%m-%dT%H:%M"),
            duration=duration,
            location=location if session_type == "in_person" else None,
            meeting_link=meeting_link if session_type == "virtual" else None,
            status="scheduled"
        )
        db.session.add(session)
        db.session.commit()
        flash("Session scheduled successfully!", "success")
        return redirect(url_for("communication.communication"))
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500