from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.user import User
from app.models.training_plan import TrainingPlan
from app.models.equipments import Equipment
from app.models.subscription import Subscription
from app.models.events import Event
from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/reports", methods=["GET"])
@jwt_required()
def reports():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Fetch basic data based on available fields
    num_members = User.query.filter_by(is_deleted=False).count()
    # Calculate avg_progress from exercises if progress exists, otherwise 0
    avg_progress = db.session.query(func.avg(func.coalesce(TrainingPlan.exercises['progress'].astext.cast(db.Float), 0))).scalar() or 0
    # Use registration_fee as revenue proxy from Events
    revenues = db.session.query(func.sum(Event.registration_fee)).scalar() or 0
    retention_rate = 92.3  # Placeholder, replace with actual logic

    # Membership types (based on Subscription plan_name)
    membership_types = [
        {"name": "Premium", "count": Subscription.query.filter_by(plan_name="Premium").count(), "color": "#4154f1"},
        {"name": "Standard", "count": Subscription.query.filter_by(plan_name="Standard").count(), "color": "#2eca6a"},
        {"name": "Basic", "count": Subscription.query.filter_by(plan_name="Basic").count(), "color": "#ff771d"}
    ]

    # Detailed metrics (adjusted to available data)
    detailed_metrics = [
        {"name": "Member Retention", "current_value": f"{retention_rate}%", "previous_value": "89.5%", "change": 2.8, "trend_icon": "bi-arrow-up", "trend_color": "success", "target": "95%", "achievement_percentage": 97.2, "achievement_color": "success", "description": "Monthly retention rate"},
        {"name": "Workout Completion", "current_value": "78.5%", "previous_value": "75.2%", "change": 3.3, "trend_icon": "bi-arrow-up", "trend_color": "success", "target": "85%", "achievement_percentage": 92.4, "achievement_color": "warning", "description": "Average workout completion rate"},
        {"name": "Revenue Growth", "current_value": f"${revenues:.2f}", "previous_value": "$11,200", "change": 11.2, "trend_icon": "bi-arrow-up", "trend_color": "success", "target": "$15,000", "achievement_percentage": 83, "achievement_color": "success", "description": "Monthly revenue from registrations"},
        {"name": "Equipment Utilization", "current_value": "67.4%", "previous_value": "62.1%", "change": 5.3, "trend_icon": "bi-arrow-up", "trend_color": "success", "target": "75%", "achievement_percentage": 89.9, "achievement_color": "warning", "description": "Average equipment usage"}
    ]

    # Coaches performance (based on User and athlete_links)
    coaches = User.query.filter_by(role='coach').limit(2).all()
    coaches_performance = [
        {
            "coach_id": c.id,
            "coach_name": c.name,
            "profile_image": c.profile_image,
            "athlete_count": len(c.athlete_links.all()),  # Convert to list with .all()
            "avg_progress": avg_progress  # Using global avg_progress as proxy
        } for c in coaches
    ]

    # Equipment usage (based on Equipment model)
    equipment_usage = [
        {"name": e.name, "usage_hours": e.usage_hours or 0, "usage_percentage": 50}  # Placeholder for usage_percentage
        for e in Equipment.query.limit(2).all()
    ]

    return render_template("admin/reports.html",
        num_members=num_members,
        avg_progress=avg_progress,
        revenues=revenues,
        retention_rate=retention_rate,
        membership_types=membership_types,
        detailed_metrics=detailed_metrics,
        coaches_performance=coaches_performance,
        equipment_usage=equipment_usage
    )

@admin_bp.route('/api/reports/update', methods=['POST'])
@jwt_required()
def update_reports():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or request.form.to_dict()
        date_range = int(data.get("date_range", 30))
        report_type = data.get("report_type", "overview")
        group_by = data.get("group_by", "week")
        compare_with = data.get("compare_with", "none")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=date_range)

        # Fetch data based on filters
        num_members = User.query.filter_by(is_deleted=False).count()
        avg_progress = db.session.query(func.avg(func.coalesce(TrainingPlan.exercises['progress'].astext.cast(db.Float), 0))).filter(TrainingPlan.created_at.between(start_date, end_date)).scalar() or 0
        revenues = db.session.query(func.sum(Event.registration_fee)).filter(Event.created_at.between(start_date, end_date)).scalar() or 0
        retention_rate = 92.3  # Placeholder

        # Chart data (adjusted to available data)
        revenue_chart_labels = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        revenue_data = [1000, revenues]  # Starting value + current revenues
        member_growth_data = [50, num_members]  # Placeholder start value

        response = {
            "success": True,
            "num_members": num_members,
            "avg_progress": avg_progress,
            "revenues": revenues,
            "retention_rate": retention_rate,
            "revenue_chart_labels": revenue_chart_labels,
            "revenue_data": revenue_data,
            "member_growth_data": member_growth_data,
            "membership_labels": ["Premium", "Standard", "Basic"],
            "membership_data": [Subscription.query.filter_by(plan_name="Premium").count(), Subscription.query.filter_by(plan_name="Standard").count(), Subscription.query.filter_by(plan_name="Basic").count()],
            "equipment_labels": [e.name for e in Equipment.query.limit(2).all()],
            "equipment_usage_data": [e.usage_hours or 0 for e in Equipment.query.limit(2).all()],
            "activity_labels": revenue_chart_labels,
            "activity_data": [30, num_members]
        }

        return jsonify(response)

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route('/api/reports/coach-performance', methods=['GET'])
@jwt_required()
def get_coach_performance():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    coaches = User.query.filter_by(role='coach').limit(5).all()
    coach_data = [
        {
            "coach_id": c.id,
            "coach_name": c.name,
            "profile_image": c.profile_image,
            "athlete_count": len(c.athlete_links),
            "avg_progress": 75.5  # Placeholder until we calculate per coach
        } for c in coaches
    ]
    return jsonify({"success": True, "coaches_performance": coach_data})

@admin_bp.route('/api/reports/equipment-usage', methods=['GET'])
@jwt_required()
def get_equipment_usage():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    equipments = Equipment.query.limit(4).all()
    equipment_data = [
        {
            "name": e.name,
            "usage_hours": e.usage_hours or 0,
            "usage_percentage": 50  # Placeholder
        } for e in equipments
    ]
    return jsonify({"success": True, "equipment_usage": equipment_data})

@admin_bp.route('/api/reports/activity-timeline', methods=['GET'])
@jwt_required()
def get_activity_timeline():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    period = request.args.get('period', 'month')
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30 if period == 'month' else 7 if period == 'week' else 365)

    labels = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
    data = [30, User.query.filter_by(is_deleted=False).count()]  # Placeholder
    return jsonify({"success": True, "activity_labels": labels, "activity_data": data})

@admin_bp.route('/api/reports/export', methods=['GET'])
@jwt_required()
def export_report():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        report_type = request.args.get("type", "overview")
        date_range = int(request.args.get("range", 30))
        flash(f"Exporting {report_type} report for {date_range} days started!", "success")
        return jsonify({
            "success": True,
            "message": "Export process initiated, check downloads"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400

@admin_bp.route('/api/reports/export-table', methods=['GET'])
@jwt_required()
def export_table():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    format = request.args.get('format', 'excel')
    return jsonify({"success": True, "message": f"Exporting table to {format}"})

@admin_bp.route('/api/reports/custom', methods=['POST'])
@jwt_required()
def custom_report():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or request.form.to_dict()
        report_name = data.get("name")
        date_from = datetime.strptime(data.get("date_from"), "%Y-%m-%d").date()
        date_to = datetime.strptime(data.get("date_to"), "%Y-%m-%d").date()
        include = data.get("include", {})

        num_members = User.query.filter_by(is_deleted=False).count()
        revenues = sum([e.registration_fee for e in Event.query.filter(Event.created_at.between(date_from, date_to)).all()]) or 0

        response = {
            "success": True,
            "report_name": report_name,
            "data": {
                "members": num_members if include.get("member_stats") else 0,
                "revenues": revenues if include.get("revenue") else 0
            },
            "message": "Custom report generated"
        }

        return jsonify(response)
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400