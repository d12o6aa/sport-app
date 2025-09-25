from flask import Blueprint, request, jsonify, render_template, flash
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy import func
from app import db
from app.models.user import User
from app.models.login_logs import LoginLog
from app.models.support_tickets import SupportTicket
from . import admin_bp

# Helper function to check admin role
def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

# Route for Support & Security Dashboard
@admin_bp.route('/support-security', methods=['GET'])
@jwt_required()
def support_security():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    # Fetch data for the dashboard
    login_logs = LoginLog.query.order_by(LoginLog.created_at.desc()).limit(20).all()
    complaints = SupportTicket.query.order_by(SupportTicket.created_at.desc()).limit(20).all()
    today = datetime.utcnow().date()
    user = User.query.get(identity)
    users = User.query.all()
    
    return render_template('admin/support_security.html',
        login_logs=login_logs,
        complaints=complaints,
        today=today,
        user=user,
        users=users
    )

# API to fetch login logs
@admin_bp.route('/api/login-logs', methods=['GET'])
@jwt_required()
def get_login_logs():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    filter_type = request.args.get('filter', 'all')
    query = LoginLog.query
    
    if filter_type == 'suspicious':
        query = query.filter(LoginLog.is_suspicious == True)
    elif filter_type == 'failed':
        query = query.filter(LoginLog.status == 'failed')
    
    logs = query.order_by(LoginLog.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "logs": [{
            "id": log.id,
            "user_name": log.user.name if log.user else "Unknown",
            "user_email": log.user.email if log.user else "Unknown",
            "ip_address": log.ip_address,
            "status": log.status,
            "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for log in logs]
    })

# API to fetch login log details
@admin_bp.route('/api/login-log/<int:log_id>', methods=['GET'])
@jwt_required()
def get_login_log_details(log_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    log = LoginLog.query.get_or_404(log_id)
    
    return jsonify({
        "success": True,
        "log": {
            "id": log.id,
            "user_name": log.user.name if log.user else "Unknown",
            "user_email": log.user.email if log.user else "Unknown",
            "ip_address": log.ip_address,
            "status": log.status,
            "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "details": getattr(log, 'details', 'No additional details')
        }
    })

# API to block IP address
@admin_bp.route('/api/block-ip', methods=['POST'])
@jwt_required()
def block_ip():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    data = request.get_json() or request.form
    ip_address = data.get('ip_address')
    reason = data.get('reason', 'Manual block')
    
    if not ip_address:
        return jsonify({"success": False, "error": "IP address is required"}), 400
    
    # TODO: Implement actual IP blocking logic with IPBlacklist model
    # For now, just simulate the action
    return jsonify({
        "success": True, 
        "message": f"IP {ip_address} blocked successfully",
        "ip": ip_address,
        "reason": reason
    })

# API to export login logs
@admin_bp.route('/api/export-login-logs', methods=['GET'])
@jwt_required()
def export_login_logs():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    # TODO: Implement actual CSV export
    return jsonify({
        "success": True, 
        "message": "Export process initiated",
        "download_url": "/admin/downloads/login_logs.csv"  # Placeholder URL
    })

# API to fetch complaints
@admin_bp.route('/api/complaints', methods=['GET'])
@jwt_required()
def get_complaints():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    status = request.args.get('status', 'all')
    query = SupportTicket.query
    
    if status != 'all':
        query = query.filter_by(status=status)
    
    complaints = query.order_by(SupportTicket.created_at.desc()).all()
    
    return jsonify({
        "success": True,
        "complaints": [{
            "id": c.id,
            "user": c.user.name if c.user else "Anonymous",
            "user_email": c.user.email if c.user else "No email",
            "subject": getattr(c, 'subject', 'No subject'),
            "content": c.content,
            "status": c.status,
            "priority": getattr(c, 'priority', 'medium'),
            "created_at": c.created_at.strftime('%Y-%m-%d %H:%M')
        } for c in complaints]
    })

# API to get single complaint details
@admin_bp.route('/api/complaints/<int:complaint_id>', methods=['GET'])
@jwt_required()
def get_complaint_details(complaint_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    complaint = SupportTicket.query.get_or_404(complaint_id)
    
    return jsonify({
        "success": True,
        "complaint": {
            "id": complaint.id,
            "user": complaint.user.name if complaint.user else "Anonymous",
            "user_email": complaint.user.email if complaint.user else "No email",
            "subject": getattr(complaint, 'subject', 'No subject'),
            "content": complaint.content,
            "status": complaint.status,
            "priority": getattr(complaint, 'priority', 'medium'),
            "created_at": complaint.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    })

# API to resolve complaint
@admin_bp.route('/api/complaints/<int:complaint_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_complaint(complaint_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    complaint = SupportTicket.query.get_or_404(complaint_id)
    complaint.status = 'resolved'
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": f"Complaint {complaint_id} marked as resolved"
    })

# API to create a new support ticket
@admin_bp.route('/api/create-support-ticket', methods=['POST'])
@jwt_required()
def create_support_ticket():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    data = request.get_json() or request.form
    user_id = data.get('user_id')
    priority = data.get('priority', 'medium')
    subject = data.get('subject')
    content = data.get('content')
    notify_user = data.get('notify_user') == 'on' or data.get('notify_user') == 'true'
    
    if not user_id or not subject or not content:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    
    # Create ticket with proper field mapping based on your model
    ticket_data = {
        'user_id': user_id,
        'priority': priority,
        'content': content,
        'status': 'pending',
        'created_at': datetime.utcnow()
    }
    
    # Add subject if your model has it
    if hasattr(SupportTicket, 'subject'):
        ticket_data['subject'] = subject
    
    ticket = SupportTicket(**ticket_data)
    
    try:
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": "Ticket created successfully",
            "ticket_id": ticket.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False, 
            "error": f"Database error: {str(e)}"
        }), 500