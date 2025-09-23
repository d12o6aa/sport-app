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
    login_logs = LoginLog.query.all()  # Assuming LoginLog model exists
    complaints = SupportTicket.query.all()  # Assuming SupportTicket model exists
    today = datetime.utcnow().date()
    user = User.query.get(identity)  # Current admin user
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
        query = query.filter(LoginLog.is_suspicious == True)  # Assuming a flag like this
    elif filter_type == 'failed':
        query = query.filter(LoginLog.status == 'failed')

    logs = query.all()
    return jsonify({
        "success": True,
        "logs": [{
            "id": log.id,
            "user_name": log.user.name if log.user else "Unknown",
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
            "ip_address": log.ip_address,
            "status": log.status,
            "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "details": log.details if hasattr(log, 'details') else "No additional details"
        }
    })

# API to block IP address
@admin_bp.route('/api/block-ip', methods=['POST'])
@jwt_required()
def block_ip():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    ip_address = request.form.get('ip_address')
    reason = request.form.get('reason', 'Manual block')

    # Assuming you have an IPBlacklist model or similar logic
    # For now, just simulate the action
    flash(f"IP {ip_address} blocked for reason: {reason}", "success")
    return jsonify({"success": True, "message": f"IP {ip_address} blocked"})

# API to export login logs
@admin_bp.route('/api/export-login-logs', methods=['GET'])
@jwt_required()
def export_login_logs():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Simulate export (in reality, generate a CSV file)
    flash("Login logs export started", "success")
    return jsonify({"success": True, "message": "Export process initiated, check downloads"})

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

    complaints = query.all()
    return jsonify({
        "success": True,
        "complaints": [{
            "id": c.id,
            "user": c.user.name if c.user else "Anonymous",
            "content": c.content,
            "status": c.status,
            "priority": c.priority,
            "created_at": c.created_at.strftime('%Y-%m-%d %H:%M')
        } for c in complaints]
    })

# API to create a new support ticket
@admin_bp.route('/api/create-support-ticket', methods=['POST'])
@jwt_required()
def create_support_ticket():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    user_id = request.form.get('user_id')
    priority = request.form.get('priority', 'medium')
    subject = request.form.get('subject')
    content = request.form.get('content')
    notify_user = request.form.get('notify_user') == 'on'

    if not user_id or not subject or not content:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    ticket = SupportTicket(
        user_id=user_id,
        priority=priority,
        subject=subject,
        content=content,
        status='pending',
        created_at=datetime.utcnow()
    )
    db.session.add(ticket)
    db.session.commit()

    flash("Support ticket created successfully", "success")
    return jsonify({"success": True, "message": "Ticket created"})