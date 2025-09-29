from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, CoachAthlete, Notification, SessionSchedule, Message
from sqlalchemy import or_, and_

from . import coach_bp

def is_user_online(user):
    """Check if user was active in the last 5 minutes"""
    if not user.last_active:
        return False
    return datetime.utcnow() - user.last_active < timedelta(minutes=5)

@coach_bp.route("/chats", methods=["GET"])
@jwt_required()
def get_chats():
    # This will be the coach-specific logic
    try:
        identity = get_jwt_identity()
        user = User.query.get(identity)
        
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        user.last_active = datetime.utcnow()
        db.session.commit()

        all_users_mode = request.args.get('all_users', 'false').lower() == 'true'
        search_query = request.args.get('search', '').strip().lower()

        if all_users_mode:
            # For the coach, you might want to show all linked athletes and other coaches
            linked_athletes_ids = [ca.athlete_id for ca in CoachAthlete.query.filter_by(coach_id=identity, is_active=True).all()]
            other_coaches_ids = [u.id for u in User.query.filter(User.role == 'coach', User.id != identity, User.is_deleted == False).all()]
            
            contact_ids = set(linked_athletes_ids + other_coaches_ids)

            contacts_query = User.query.filter(
                User.id.in_(contact_ids),
                User.is_deleted == False,
                User.status == 'active'
            )
            
            if search_query:
                contacts_query = contacts_query.filter(
                    or_(
                        User.name.ilike(f'%{search_query}%'),
                        User.email.ilike(f'%{search_query}%')
                    )
                )

            contacts = contacts_query.all()
            
            users_list = []
            for contact in contacts:
                is_online = is_user_online(contact)
                last_seen = ""
                if not is_online and contact.last_active:
                    time_diff = datetime.utcnow() - contact.last_active
                    if time_diff.days > 0:
                        last_seen = f"{time_diff.days}d ago"
                    elif time_diff.seconds >= 3600:
                        last_seen = f"{time_diff.seconds // 3600}h ago"
                    elif time_diff.seconds >= 60:
                        last_seen = f"{time_diff.seconds // 60}m ago"
                    else:
                        last_seen = "Just now"

                profile_image_url = url_for('static', filename=f'uploads/{contact.profile_image}') if contact.profile_image and contact.profile_image != 'default.jpg' else url_for('static', filename='images/default.jpg')

                users_list.append({
                    "id": contact.id,
                    "name": contact.name,
                    "email": contact.email,
                    "role": contact.role,
                    "profile_image": profile_image_url,
                    "is_online": is_online,
                    "last_seen": last_seen,
                })

            return jsonify(users_list)

        # Original logic for existing chats
        linked_athletes_ids = [
            ca.athlete_id for ca in CoachAthlete.query.filter_by(
                coach_id=identity, 
                is_active=True
            ).all()
        ]
        
        message_contacts_subquery = db.session.query(Message.sender_id).filter(
            Message.receiver_id == identity
        ).union(
            db.session.query(Message.receiver_id).filter(
                Message.sender_id == identity
            )
        )
        message_contacts_ids = [row[0] for row in message_contacts_subquery.all()]
        
        all_contact_ids = set(linked_athletes_ids + message_contacts_ids)
        all_contact_ids.discard(identity)
        
        if not all_contact_ids:
            return jsonify([])
        
        contacts_query = User.query.filter(
            User.id.in_(all_contact_ids),
            User.is_deleted == False,
            User.status == 'active'
        )
        
        if search_query:
            contacts_query = contacts_query.filter(
                or_(
                    User.name.ilike(f'%{search_query}%'),
                    User.email.ilike(f'%{search_query}%')
                )
            )
        
        contacts = contacts_query.all()
        
        chats = []
        for contact in contacts:
            last_message = Message.query.filter(
                or_(
                    and_(Message.sender_id == identity, Message.receiver_id == contact.id),
                    and_(Message.sender_id == contact.id, Message.receiver_id == identity)
                )
            ).order_by(Message.sent_at.desc()).first()
            
            unread_count = Message.query.filter(
                Message.sender_id == contact.id,
                Message.receiver_id == identity,
                Message.is_read == False
            ).count()
            
            is_online = is_user_online(contact)
            
            last_seen = ""
            if not is_online and contact.last_active:
                time_diff = datetime.utcnow() - contact.last_active
                if time_diff.days > 0:
                    last_seen = f"{time_diff.days}d ago"
                elif time_diff.seconds >= 3600:
                    last_seen = f"{time_diff.seconds // 3600}h ago"
                elif time_diff.seconds >= 60:
                    last_seen = f"{time_diff.seconds // 60}m ago"
                else:
                    last_seen = "Just now"
            
            profile_image_url = url_for('static', filename=f'uploads/{contact.profile_image}') if contact.profile_image and contact.profile_image != 'default.jpg' else url_for('static', filename='images/default.jpg')
            
            chats.append({
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "role": contact.role,
                "profile_image": profile_image_url,
                "last_message": last_message.content if last_message else "No messages yet",
                "last_message_time": last_message.sent_at.strftime("%I:%M %p") if last_message else "",
                "last_message_date": last_message.sent_at.isoformat() if last_message else None,
                "is_online": is_online,
                "last_seen": last_seen,
                "unread_count": unread_count,
                "is_sender": last_message.sender_id == identity if last_message else False
            })
        
        chats.sort(key=lambda x: x['last_message_date'] if x['last_message_date'] else '', reverse=True)
        
        return jsonify(chats)
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in coach get_chats: {str(e)}")
        return jsonify({"msg": "Internal server error"}), 500


@coach_bp.route("/messages/<int:contact_id>", methods=["GET"])
@jwt_required()
def get_messages(contact_id):
    """Get all messages between current user and contact"""
    try:
        identity = get_jwt_identity()
        
        # Verify contact exists
        contact = User.query.get(contact_id)
        if not contact:
            return jsonify({"msg": "Contact not found"}), 404
        
        # Mark messages as read
        unread_messages = Message.query.filter(
            Message.sender_id == contact_id,
            Message.receiver_id == identity,
            Message.is_read == False
        ).all()
        
        for msg in unread_messages:
            msg.is_read = True
        
        if unread_messages:
            db.session.commit()
        
        # Fetch all messages
        messages = Message.query.filter(
            or_(
                and_(Message.sender_id == identity, Message.receiver_id == contact_id),
                and_(Message.sender_id == contact_id, Message.receiver_id == identity)
            )
        ).order_by(Message.sent_at.asc()).all()
        
        return jsonify([
            {
                "id": msg.id,
                "sender_id": msg.sender_id,
                "content": msg.content,
                "sent_at": msg.sent_at.isoformat(),
                "is_read": msg.is_read
            }
            for msg in messages
        ])
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in get_messages: {str(e)}")
        return jsonify({"msg": "Internal server error"}), 500
    

@coach_bp.route("/send_message", methods=["POST"])
@jwt_required()
def send_message():
    """Send a new message"""
    try:
        identity = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({"msg": "No data provided"}), 400
        
        receiver_id = data.get("receiver_id")
        content = data.get("content", "").strip()

        if not receiver_id or not content:
            return jsonify({"msg": "Receiver ID and content are required"}), 400

        # Verify receiver exists
        receiver = User.query.get(receiver_id)
        if not receiver or receiver.is_deleted or receiver.status != 'active':
            return jsonify({"msg": "Receiver not found or inactive"}), 404

        # Create message
        new_message = Message(
            sender_id=identity,
            receiver_id=receiver_id,
            content=content,
            sent_at=datetime.utcnow(),
            is_read=False
        )
        
        db.session.add(new_message)
        db.session.commit()
        
        return jsonify({
            "msg": "Message sent successfully",
            "message": {
                "id": new_message.id,
                "sender_id": new_message.sender_id,
                "content": new_message.content,
                "sent_at": new_message.sent_at.isoformat(),
                "is_read": new_message.is_read
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in send_message: {str(e)}")
        return jsonify({"msg": "Internal server error"}), 500

@coach_bp.route("/communication", methods=["GET"])
@jwt_required()
def communication():
    try:
        identity = get_jwt_identity()
        user = User.query.get(identity)
        
        if not user:
            return jsonify({"msg": "User not found"}), 404
        
        return render_template(
            "coach/communication.html", 
            user_id=identity, 
            user_name=user.name
        )
        
    except Exception as e:
        print(f"Error in coach communication: {str(e)}")
        return jsonify({"msg": "Internal server error"}), 500
