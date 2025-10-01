from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app import db
from app.models import User, Message
from sqlalchemy import func, and_, or_, case, distinct
from app import socketio

from . import coach_bp



@coach_bp.route("/chats", methods=["GET"])
@jwt_required()
def get_chats():
    try:
        identity = get_jwt_identity()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search_query = request.args.get('search', '').strip()
        all_users_mode = request.args.get('all_users', 'false').lower() == 'true'

        if all_users_mode:
            users_query = User.query.filter(
                User.id != identity,
                User.is_deleted.is_(False),
                User.status == 'active'
            )
            if search_query:
                users_query = users_query.filter(
                    or_(
                        User.name.ilike(f'%{search_query}%'),
                        User.email.ilike(f'%{search_query}%')
                    )
                )
            users = users_query.all()
            users_data = [
                {
                    'id': user.id,
                    'name': user.name,
                    'profile_image': user.profile_image or '/static/images/default.jpg',
                    'is_online': user.status == 'active' and user.last_active > func.now() - func.interval('15 minutes'),
                    'last_seen': user.last_active.isoformat() if user.last_active else None
                } for user in users
            ]
            return jsonify({'users': users_data})

        # Subquery for latest message per user
        latest_message_subquery = db.session.query(
            Message,
            func.row_number().over(
                partition_by=case(
                    [(Message.sender_id != identity, Message.sender_id)],
                    else_=Message.receiver_id
                ),
                order_by=Message.sent_at.desc()
            ).label('rn')
        ).filter(
            or_(
                Message.sender_id == identity,
                Message.receiver_id == identity
            )
        ).subquery()

        # Main query
        query = db.session.query(
            User,
            latest_message_subquery.c.id.label('message_id'),
            latest_message_subquery.c.content.label('last_message'),
            latest_message_subquery.c.sent_at.label('last_message_time'),
            latest_message_subquery.c.sender_id.label('message_sender_id'),
            func.count(
                func.distinct(
                    case(
                        [(and_(Message.is_read.is_(False), Message.receiver_id == identity, Message.sender_id == User.id), Message.id)],
                        else_=None
                    )
                )
            ).label('unread_count')
        ).join(
            latest_message_subquery,
            or_(
                and_(
                    User.id == latest_message_subquery.c.sender_id,
                    User.id != identity
                ),
                and_(
                    User.id == latest_message_subquery.c.receiver_id,
                    User.id != identity
                )
            )
        ).outerjoin(
            Message,
            and_(
                Message.sender_id == User.id,
                Message.receiver_id == identity
            )
        ).filter(
            User.is_deleted.is_(False),
            User.status == 'active',
            or_(
                latest_message_subquery.c.sender_id == identity,
                latest_message_subquery.c.receiver_id == identity
            )
        ).group_by(
            User.id,
            latest_message_subquery.c.id,
            latest_message_subquery.c.content,
            latest_message_subquery.c.sent_at,
            latest_message_subquery.c.sender_id
        ).order_by(
            latest_message_subquery.c.sent_at.desc()
        )

        if search_query:
            query = query.filter(
                or_(
                    User.name.ilike(f'%{search_query}%'),
                    User.email.ilike(f'%{search_query}%')
                )
            )

        messages = query.paginate(page=page, per_page=per_page, error_out=False)

        chats = []
        for user, message_id, last_message, last_message_time, message_sender_id, unread_count in messages.items:
            chats.append({
                'id': user.id,
                'name': user.name,
                'profile_image': user.profile_image or '/static/images/default.jpg',
                'last_message': last_message or '',
                'last_message_time': last_message_time.isoformat() if last_message_time else '',
                'is_online': user.status == 'active' and user.last_active > func.now() - func.interval('15 minutes'),
                'last_seen': user.last_active.isoformat() if user.last_active else None,
                'unread_count': unread_count,
                'is_sender': message_sender_id == identity if message_id else False
            })

        return jsonify({
            'chats': chats,
            'total': messages.total,
            'pages': messages.pages,
            'page': page
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error in get_chats: {str(e)}")
        return jsonify({"msg": "Internal server error"}), 500

def format_last_seen(last_active):
    if not last_active:
        return ""
    time_diff = datetime.utcnow() - last_active
    if time_diff.days > 0:
        return f"{time_diff.days}d ago"
    elif time_diff.seconds >= 3600:
        return f"{time_diff.seconds // 3600}h ago"
    elif time_diff.seconds >= 60:
        return f"{time_diff.seconds // 60}m ago"
    return "Just now"

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
    data = request.get_json()
    if not data:
        return jsonify({"msg": "No data provided"}), 400
    
    receiver_id = data.get("receiver_id")
    content = data.get("content", "").strip()

    if not receiver_id or not content:
        return jsonify({"msg": "Receiver ID and content are required"}), 400

    receiver = User.query.get(receiver_id)
    if not receiver or receiver.is_deleted or receiver.status != 'active':
        return jsonify({"msg": "Receiver not found or inactive"}), 404

    new_message = Message(
        sender_id=get_jwt_identity(),
        receiver_id=receiver_id,
        content=content,
        sent_at=datetime.utcnow(),
        is_read=False
    )
    db.session.add(new_message)
    db.session.commit()

    socketio.emit('new_message', {
        'id': new_message.id,
        'sender_id': new_message.sender_id,
        'content': new_message.content,
        'sent_at': new_message.sent_at.isoformat(),
        'is_read': new_message.is_read
    }, broadcast=True)

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
