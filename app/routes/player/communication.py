from flask import Blueprint, request, jsonify, render_template, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models import User, CoachAthlete, Message
from sqlalchemy import or_

from . import athlete_bp

# ... (دالة is_athlete)
def is_athlete(user_id):
    user = User.query.get(user_id)
    return user and user.is_athlete

# Route to get the chats list for the athlete
@athlete_bp.route("/chats", methods=["GET"])
@jwt_required()
def get_chats():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    
    if not user or not user.is_athlete:
        return jsonify({"msg": "Unauthorized"}), 403

    # Fetch all coaches linked to the current athlete
    linked_coaches = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.coach_id == User.id)
        .filter(CoachAthlete.athlete_id == identity, CoachAthlete.is_active == True)
        .all()
    )

    # Fetch all athletes linked to the current coach (if user is a coach)
    # Note: this part is for a coach's view, we'll keep it for symmetry, but for an athlete it will be empty
    linked_athletes = (
        db.session.query(User)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == identity, CoachAthlete.is_active == True)
        .all()
    )

    # Combine all unique contacts
    contacts = list(set(linked_coaches + linked_athletes))

    # A more robust way to get all contacts:
    # Get all users who have chatted with the current user, or are linked to them.
    all_contacts_ids = db.session.query(Message.sender_id).filter(Message.receiver_id == identity).union(
        db.session.query(Message.receiver_id).filter(Message.sender_id == identity)
    )
    all_contacts_ids = [row[0] for row in all_contacts_ids.all()]

    coaches_ids = [c.coach_id for c in CoachAthlete.query.filter_by(athlete_id=identity).all()]
    all_ids_to_fetch = set(all_contacts_ids + coaches_ids)
    
    # Exclude the current user from the list
    all_ids_to_fetch.discard(identity)
    
    contacts = User.query.filter(User.id.in_(all_ids_to_fetch)).all()
    
    chats = []
    for contact in contacts:
        last_message = Message.query.filter(
            or_(
                (Message.sender_id == identity and Message.receiver_id == contact.id),
                (Message.sender_id == contact.id and Message.receiver_id == identity)
            )
        ).order_by(Message.sent_at.desc()).first()
        
        # Determine online status - for now, this is a placeholder
        # You would need a real-time system (like WebSockets) to get this data
        is_online = False # Placeholder for now

        chats.append({
            "id": contact.id,
            "name": contact.name,
            "profile_image": url_for('static', filename=f'uploads/{contact.profile_image}' if contact.profile_image else 'default.jpg'),
            "last_message": last_message.content if last_message else "No messages yet.",
            "last_message_time": last_message.sent_at.strftime("%I:%M %p") if last_message else "",
            "is_online": is_online
        })
    
    # Sort chats by the last message time
    chats.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    return jsonify(chats)

# Route to get messages for a specific chat
@athlete_bp.route("/messages/<int:contact_id>", methods=["GET"])
@jwt_required()
def get_messages(contact_id):
    identity = get_jwt_identity()
    
    messages = Message.query.filter(
        or_(
            (Message.sender_id == identity and Message.receiver_id == contact_id),
            (Message.sender_id == contact_id and Message.receiver_id == identity)
        )
    ).order_by(Message.sent_at.asc()).all()
    
    return jsonify([
        {
            "sender_id": msg.sender_id,
            "content": msg.content,
            "sent_at": msg.sent_at.isoformat()
        }
        for msg in messages
    ])

# Route to send a message
@athlete_bp.route("/send_message", methods=["POST"])
@jwt_required()
def send_message():
    identity = get_jwt_identity()
    data = request.json
    receiver_id = data.get("receiver_id")
    content = data.get("content")

    if not receiver_id or not content:
        return jsonify({"msg": "Receiver ID and content are required"}), 400

    try:
        new_message = Message(
            sender_id=identity,
            receiver_id=receiver_id,
            content=content,
            sent_at=datetime.utcnow()
        )
        db.session.add(new_message)
        db.session.commit()
        return jsonify({"msg": "Message sent successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# Main communication route (just renders the template)
@athlete_bp.route("/communication", methods=["GET"])
@jwt_required()
def communication():
    identity = get_jwt_identity()
    if not is_athlete(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    # Pass the user's ID to the template
    return render_template("athlete/communication.html", user_id=identity)