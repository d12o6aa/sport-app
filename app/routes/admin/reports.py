from flask import Blueprint, request, jsonify, render_template,current_app
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
from sqlalchemy import or_
import logging
from app.models.subscription_plans import SubscriptionPlan
from app.models.subscription_usage import SubscriptionUsage
from app.models.payments import Payment
from app.models.coach_athlete import CoachAthlete

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

def format_change(value):
    """Format a numerical change with + or - sign and one decimal place."""
    if value is None:
        return "0.0%"
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}%"

def register_filters(app):
    """Register custom Jinja2 filters."""
    app.jinja_env.filters['format_change'] = format_change

def get_membership_types(start_date, end_date):
    """Generate a list of membership types with their counts for a given date range"""
    try:
        color_map = {
            "Premium": "#4154f1",
            "Standard": "#2eca6a",
            "Basic": "#ff771d",
            "Enterprise": "#ff2d55"
        }
        plans = SubscriptionPlan.query.filter_by(is_active=True).all()
        membership_types = [
            {
                "name": plan.name,
                "count": Subscription.query
                    .join(SubscriptionPlan)
                    .filter(SubscriptionPlan.id == Subscription.plan_id)
                    .filter(SubscriptionPlan.name == plan.name)
                    .filter(Subscription.created_at.between(start_date, end_date))
                    .count(),
                "color": color_map.get(plan.name, "#6c757d")
            }
            for plan in plans
        ]
        return membership_types
    except Exception as e:
        logger.error(f"Error generating membership types: {str(e)}")
        return []

def calculate_retention_rate(start_date, end_date):
    """Calculate retention rate based on active subscriptions"""
    try:
        active_at_start = Subscription.query.filter(
            Subscription.status.in_(['active', 'trial']),
            Subscription.created_at <= start_date
        ).count()
        active_at_end = Subscription.query.filter(
            Subscription.status.in_(['active', 'trial']),
            Subscription.created_at <= start_date,
            Subscription.end_date >= end_date
        ).count()
        return (active_at_end / active_at_start * 100) if active_at_start > 0 else 0
    except Exception as e:
        logger.error(f"Error calculating retention rate: {str(e)}")
        return 0

@admin_bp.route('/reports', methods=['GET'])
@jwt_required()
def reports():
    """Render the reports page with membership metrics"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Define date range (e.g., last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        # Query parameters for custom date range
        start = request.args.get('start_date')
        end = request.args.get('end_date')
        if start and end:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d')
                end_date = datetime.strptime(end, '%Y-%m-%d')
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Metrics
        num_members = User.query.filter_by(role='athlete').filter(User.created_at.between(start_date, end_date)).count()
        avg_progress = db.session.query(
            func.avg(
                func.coalesce(
                    (SubscriptionUsage.usage_count / func.nullif(SubscriptionUsage.usage_limit, 0) * 100),
                    0
                )
            )
        )\
            .filter(SubscriptionUsage.feature == 'workouts')\
            .filter(SubscriptionUsage.period_start.between(start_date, end_date))\
            .scalar() or 0
        revenues = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'completed')\
            .filter(Payment.processed_at.between(start_date, end_date))\
            .scalar() or 0
        retention_rate = calculate_retention_rate(start_date, end_date)

        # Membership types
        membership_types = get_membership_types(start_date, end_date)

        # Previous period for comparison
        previous_start = start_date - timedelta(days=30)
        previous_revenues = db.session.query(func.sum(Payment.amount))\
            .filter(Payment.status == 'completed')\
            .filter(Payment.processed_at.between(previous_start, start_date))\
            .scalar() or 0
        previous_retention = calculate_retention_rate(previous_start, start_date)
        previous_progress = db.session.query(
            func.avg(
                func.coalesce(
                    (SubscriptionUsage.usage_count / func.nullif(SubscriptionUsage.usage_limit, 0) * 100),
                    0
                )
            )
        )\
            .filter(SubscriptionUsage.feature == 'workouts')\
            .filter(SubscriptionUsage.period_start.between(previous_start, start_date))\
            .scalar() or 0
        equipment_usage_current = 0  # Placeholder
        equipment_usage_previous = 0  # Placeholder

        detailed_metrics = [
            {
                "name": "Member Retention",
                "current_value": f"{retention_rate:.1f}%",
                "previous_value": f"{previous_retention:.1f}%",
                "change": retention_rate - previous_retention,
                "trend_icon": "bi-arrow-up" if retention_rate >= previous_retention else "bi-arrow-down",
                "trend_color": "success" if retention_rate >= previous_retention else "danger",
                "target": "95%",
                "achievement_percentage": (retention_rate / 95 * 100),
                "achievement_color": "success" if retention_rate >= 95 else "warning",
                "description": "Monthly retention rate"
            },
            {
                "name": "Workout Completion",
                "current_value": f"{avg_progress:.1f}%",
                "previous_value": f"{previous_progress:.1f}%",
                "change": avg_progress - previous_progress,
                "trend_icon": "bi-arrow-up" if avg_progress >= previous_progress else "bi-arrow-down",
                "trend_color": "success" if avg_progress >= previous_progress else "danger",
                "target": "85%",
                "achievement_percentage": (avg_progress / 85 * 100),
                "achievement_color": "success" if avg_progress >= 85 else "warning",
                "description": "Average workout completion rate"
            },
            {
                "name": "Revenue Growth",
                "current_value": f"${revenues:.2f}",
                "previous_value": f"${previous_revenues:.2f}",
                "change": ((revenues - previous_revenues) / previous_revenues * 100) if previous_revenues > 0 else 0,
                "trend_icon": "bi-arrow-up" if revenues >= previous_revenues else "bi-arrow-down",
                "trend_color": "success" if revenues >= previous_revenues else "danger",
                "target": "$15000",
                "achievement_percentage": (revenues / 15000 * 100),
                "achievement_color": "success" if revenues >= 15000 else "warning",
                "description": "Monthly revenue from subscriptions"
            },
            {
                "name": "Equipment Utilization",
                "current_value": f"{equipment_usage_current:.1f}%",
                "previous_value": f"{equipment_usage_previous:.1f}%",
                "change": equipment_usage_current - equipment_usage_previous,
                "trend_icon": "bi-arrow-up" if equipment_usage_current >= equipment_usage_previous else "bi-arrow-down",
                "trend_color": "success" if equipment_usage_current >= equipment_usage_previous else "danger",
                "target": "75%",
                "achievement_percentage": (equipment_usage_current / 75 * 100),
                "achievement_color": "success" if equipment_usage_current >= 75 else "warning",
                "description": "Average equipment usage (placeholder)"
            }
        ]

        # Coaches performance
        coaches = User.query.filter_by(role='coach').limit(2).all()
        coaches_performance = [
            {
                "coach_id": c.id,
                "coach_name": c.name,
                "profile_image": c.profile_image or '/static/images/default.jpg',
                "athlete_count": c.athlete_links.count(),
                "avg_progress": db.session.query(
                    func.avg(
                        func.coalesce(
                            (SubscriptionUsage.usage_count / func.nullif(SubscriptionUsage.usage_limit, 0) * 100),
                            0
                        )
                    )
                )
                    .join(Subscription, SubscriptionUsage.subscription_id == Subscription.id)
                    .join(CoachAthlete, Subscription.user_id == CoachAthlete.athlete_id)
                    .filter(CoachAthlete.coach_id == c.id)
                    .filter(SubscriptionUsage.feature == 'workouts')
                    .filter(SubscriptionUsage.period_start.between(start_date, end_date))
                    .scalar() or 0
            } for c in coaches
        ]

        # Equipment usage (placeholder)
        equipment_usage = [
            {
                "name": "Placeholder Equipment",
                "usage_hours": 0,
                "usage_percentage": 50
            }
        ]

        return render_template(
            "admin/reports.html",
            num_members=num_members,
            avg_progress=avg_progress,
            revenues=revenues,
            retention_rate=retention_rate,
            membership_types=membership_types,
            detailed_metrics=detailed_metrics,
            coaches_performance=coaches_performance,
            equipment_usage=equipment_usage
        )
    except Exception as e:
        logger.error(f"Error rendering reports page: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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

        # Fetch dynamic data
        num_members = User.query.filter_by(is_deleted=False).filter(User.created_at.between(start_date, end_date)).count()
        avg_progress = db.session.query(func.avg(func.coalesce(TrainingPlan.exercises['progress'].astext.cast(db.Float), 0))).filter(TrainingPlan.created_at.between(start_date, end_date)).scalar() or 0
        revenues = db.session.query(func.sum(Event.registration_fee)).filter(Event.created_at.between(start_date, end_date)).scalar() or 0
        retention_rate = calculate_retention_rate(start_date, end_date)

        # Dynamic chart data
        if group_by == "day":
            date_format = "%Y-%m-%d"
            interval = timedelta(days=1)
        elif group_by == "week":
            date_format = "%Y-%W"
            interval = timedelta(weeks=1)
        else:  # month
            date_format = "%Y-%m"
            interval = timedelta(days=30)

        revenue_chart_labels = []
        revenue_data = []
        member_growth_data = []
        activity_data = []

        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + interval
            revenue_chart_labels.append(current_date.strftime(date_format))
            revenue_data.append(
                db.session.query(func.sum(Event.registration_fee))
                .filter(Event.created_at.between(current_date, next_date)).scalar() or 0
            )
            member_growth_data.append(
                User.query.filter_by(is_deleted=False)
                .filter(User.created_at.between(current_date, next_date)).count()
            )
            activity_data.append(
                User.query.filter_by(is_deleted=False)
                .filter(User.last_active.between(current_date, next_date)).count()
            )
            current_date = next_date

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
            "membership_data": [
                Subscription.query.filter_by(plan_name="Premium").filter(Subscription.created_at.between(start_date, end_date)).count(),
                Subscription.query.filter_by(plan_name="Standard").filter(Subscription.created_at.between(start_date, end_date)).count(),
                Subscription.query.filter_by(plan_name="Basic").filter(Subscription.created_at.between(start_date, end_date)).count()
            ],
            "equipment_labels": [e.name for e in Equipment.query.filter(Equipment.last_used.between(start_date, end_date)).limit(2).all()],
            "equipment_usage_data": [e.usage_hours or 0 for e in Equipment.query.filter(Equipment.last_used.between(start_date, end_date)).limit(2).all()],
            "activity_labels": revenue_chart_labels,
            "activity_data": activity_data
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
        date_from_str = data.get("date_from")
        date_to_str = data.get("date_to")
        include = data.get("include", {})

        if not all([report_name, date_from_str, date_to_str]):
            return jsonify({"success": False, "error": "Missing required fields: name, date_from, date_to"}), 400

        try:
            date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            date_to = datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Invalid date format, expected YYYY-MM-DD"}), 400

        if date_to < date_from:
            return jsonify({"success": False, "error": "date_to must be after date_from"}), 400

        num_members = User.query.filter_by(is_deleted=False).filter(User.created_at.between(date_from, date_to)).count()
        revenues = db.session.query(func.sum(Event.registration_fee)).filter(Event.created_at.between(date_from, date_to)).scalar() or 0
        # Add more dynamic metrics based on `include`

        response = {
            "success": True,
            "report_name": report_name,
            "data": {
                "members": num_members if include.get("member_stats") else 0,
                "revenues": revenues if include.get("revenue") else 0,
                # Add more metrics as needed
            },
            "message": "Custom report generated"
        }

        return jsonify(response)
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Custom report failed: {str(e)}"}), 400