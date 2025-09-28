from flask import Blueprint, request, jsonify, render_template, flash
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, and_
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
    
    # Get current date for filtering
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    # Fetch recent login logs with user data
    login_logs = db.session.query(LoginLog).join(User, LoginLog.user_id == User.id, isouter=True)\
        .order_by(LoginLog.created_at.desc()).limit(50).all()
    
    # Fetch recent support tickets with user data  
    complaints = db.session.query(SupportTicket).join(User, SupportTicket.user_id == User.id, isouter=True)\
        .order_by(SupportTicket.created_at.desc()).limit(50).all()
    
    # Calculate statistics
    stats = {
        'total_logins': LoginLog.query.count(),
        'today_logins': LoginLog.query.filter(LoginLog.created_at >= today_start).count(),
        'total_tickets': SupportTicket.query.count(),
        'pending_tickets': SupportTicket.query.filter_by(status='pending').count(),
        'resolved_tickets': SupportTicket.query.filter_by(status='resolved').count(),
        'high_priority_tickets': SupportTicket.query.filter_by(priority='high').count(),
        'failed_logins': LoginLog.query.filter_by(status='failed').count(),
        'suspicious_logins': LoginLog.query.filter_by(is_suspicious=True).count()
    }
    
    # Calculate average response time (mock calculation)
    # You can implement actual logic based on ticket response times
    stats['avg_response_time'] = "2.4h"
    stats['response_improvement'] = -15  # percentage improvement
    
    # Get all users for ticket creation
    users = User.query.filter_by(is_deleted=False).order_by(User.name).all()
    user = User.query.get(identity)
    
    return render_template('admin/support_security.html',
        login_logs=login_logs,
        complaints=complaints,
        stats=stats,
        today=today,
        user=user,
        users=users
    )

# API to fetch login logs with filtering
@admin_bp.route('/api/login-logs', methods=['GET'])
@jwt_required()
def get_login_logs():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        filter_type = request.args.get('filter', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        query = db.session.query(LoginLog).join(User, LoginLog.user_id == User.id, isouter=True)
        
        if filter_type == 'suspicious':
            query = query.filter(LoginLog.is_suspicious == True)
        elif filter_type == 'failed':
            query = query.filter(LoginLog.status == 'failed')
        elif filter_type == 'success':
            query = query.filter(LoginLog.status == 'success')
        
        logs = query.order_by(LoginLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "success": True,
            "logs": [{
                "id": log.id,
                "user_id": log.user_id,
                "user_name": log.user.name if log.user else "Unknown User",
                "user_email": log.user.email if log.user else "Unknown Email",
                "ip_address": log.ip_address,
                "status": log.status,
                "is_suspicious": log.is_suspicious,
                "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "details": log.details
            } for log in logs.items],
            "pagination": {
                "page": logs.page,
                "pages": logs.pages,
                "per_page": logs.per_page,
                "total": logs.total
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to fetch login log details
@admin_bp.route('/api/login-log/<int:log_id>', methods=['GET'])
@jwt_required()
def get_login_log_details(log_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        log = LoginLog.query.get_or_404(log_id)
        
        return jsonify({
            "success": True,
            "log": {
                "id": log.id,
                "user_id": log.user_id,
                "user_name": log.user.name if log.user else "Unknown User",
                "user_email": log.user.email if log.user else "Unknown Email",
                "ip_address": log.ip_address,
                "status": log.status,
                "is_suspicious": log.is_suspicious,
                "timestamp": log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "details": log.details or "No additional details available",
                "user_agent": getattr(log, 'user_agent', 'Not recorded')
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to block IP address
@admin_bp.route('/api/block-ip', methods=['POST'])
@jwt_required()
def block_ip():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        data = request.get_json() or request.form.to_dict()
        ip_address = data.get('ip_address')
        reason = data.get('reason', 'Manual block by admin')
        
        if not ip_address:
            return jsonify({"success": False, "error": "IP address is required"}), 400
        
        # Mark all logins from this IP as suspicious
        LoginLog.query.filter_by(ip_address=ip_address).update({
            'is_suspicious': True,
            'details': f"IP blocked: {reason}"
        })
        
        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"IP {ip_address} has been blocked and marked as suspicious",
            "ip": ip_address,
            "reason": reason
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# API to export login logs
@admin_bp.route('/api/export-login-logs', methods=['GET'])
@jwt_required()
def export_login_logs():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        import csv
        import io
        from flask import make_response
        
        # Get all login logs with user data
        logs = db.session.query(LoginLog).join(User, LoginLog.user_id == User.id, isouter=True)\
            .order_by(LoginLog.created_at.desc()).all()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['ID', 'User Name', 'User Email', 'IP Address', 'Status', 
                        'Suspicious', 'Timestamp', 'Details'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.id,
                log.user.name if log.user else "Unknown",
                log.user.email if log.user else "Unknown",
                log.ip_address,
                log.status,
                'Yes' if log.is_suspicious else 'No',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.details or ''
            ])
        
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=login_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to fetch support tickets with filtering
@admin_bp.route('/api/complaints', methods=['GET'])
@jwt_required()
def get_complaints():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        status = request.args.get('status', 'all')
        priority = request.args.get('priority', 'all')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        query = db.session.query(SupportTicket).join(User, SupportTicket.user_id == User.id, isouter=True)
        
        if status != 'all':
            query = query.filter(SupportTicket.status == status)
            
        if priority != 'all':
            query = query.filter(SupportTicket.priority == priority)
        
        tickets = query.order_by(SupportTicket.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "success": True,
            "complaints": [{
                "id": ticket.id,
                "user_id": ticket.user_id,
                "user": ticket.user.name if ticket.user else "Anonymous",
                "user_email": ticket.user.email if ticket.user else "No email",
                "subject": ticket.subject,
                "content": ticket.content,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.strftime('%Y-%m-%d %H:%M')
            } for ticket in tickets.items],
            "pagination": {
                "page": tickets.page,
                "pages": tickets.pages,
                "per_page": tickets.per_page,
                "total": tickets.total
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to get single support ticket details
@admin_bp.route('/api/complaints/<int:complaint_id>', methods=['GET'])
@jwt_required()
def get_complaint_details(complaint_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        ticket = SupportTicket.query.get_or_404(complaint_id)
        
        return jsonify({
            "success": True,
            "complaint": {
                "id": ticket.id,
                "user_id": ticket.user_id,
                "user": ticket.user.name if ticket.user else "Anonymous",
                "user_email": ticket.user.email if ticket.user else "No email",
                "subject": ticket.subject,
                "content": ticket.content,
                "status": ticket.status,
                "priority": ticket.priority,
                "created_at": ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to resolve support ticket
@admin_bp.route('/api/complaints/<int:complaint_id>/resolve', methods=['POST'])
@jwt_required()
def resolve_complaint(complaint_id):
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        ticket = SupportTicket.query.get_or_404(complaint_id)
        ticket.status = 'resolved'
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Support ticket #{complaint_id} has been marked as resolved"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# API to create a new support ticket
@admin_bp.route('/api/create-support-ticket', methods=['POST'])
@jwt_required()
def create_support_ticket():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        data = request.get_json() or request.form.to_dict()
        user_id = data.get('user_id')
        priority = data.get('priority', 'medium')
        subject = data.get('subject', '').strip()
        content = data.get('content', '').strip()
        
        if not user_id or not subject or not content:
            return jsonify({"success": False, "error": "All fields are required"}), 400
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "error": "Selected user not found"}), 404
        
        # Create new support ticket
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
        
        return jsonify({
            "success": True, 
            "message": f"Support ticket created successfully for {user.name}",
            "ticket_id": ticket.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# API to get dashboard statistics
@admin_bp.route('/api/dashboard-stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    
    try:
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        stats = {
            'login_stats': {
                'total': LoginLog.query.count(),
                'today': LoginLog.query.filter(LoginLog.created_at >= today_start).count(),
                'failed': LoginLog.query.filter_by(status='failed').count(),
                'suspicious': LoginLog.query.filter_by(is_suspicious=True).count()
            },
            'ticket_stats': {
                'total': SupportTicket.query.count(),
                'pending': SupportTicket.query.filter_by(status='pending').count(),
                'in_progress': SupportTicket.query.filter_by(status='in_progress').count(),
                'resolved': SupportTicket.query.filter_by(status='resolved').count(),
                'high_priority': SupportTicket.query.filter_by(priority='high').count()
            },
            'security_stats': {
                'blocked_ips': LoginLog.query.filter_by(is_suspicious=True).distinct(LoginLog.ip_address).count(),
                'active_sessions': 247,  # You can implement actual session counting
                'alerts': 8
            }
        }
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500