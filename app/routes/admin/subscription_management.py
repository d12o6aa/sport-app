from flask import Blueprint, jsonify, render_template, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import User, Subscription, SubscriptionPlan, Payment, PaymentMethod, SubscriptionUsage
from datetime import datetime, timedelta
from sqlalchemy import func
import logging
from datetime import timezone


from . import admin_bp  # Assuming admin_bp is defined in __init__.py of the admin package

def is_admin(identity):
    """Check if the user is an admin"""
    user = User.query.filter_by(id=identity).first()
    return user and user.role == 'admin'

def get_membership_types(start_date=None, end_date=None):
    """Generate a list of membership types with their counts for a given date range"""
    try:
        if start_date is None:
            end_date = datetime.now(tz=timezone.utc)
            start_date = end_date - timedelta(days=30)
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
        return []

def format_change(value):
    """Format percentage change for display"""
    if value is None:
        return "0.0%"
    if value > 0:
        return f"+{value:.1f}%"
    elif value < 0:
        return f"{value:.1f}%"
    return "0.0%"

@admin_bp.route('/subscriptions', methods=['GET'])
@jwt_required()
def subscriptions():
    """Render the subscriptions management page"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        num_subscribers = Subscription.query.filter(Subscription.status.in_(['active', 'trial'])).count()
        revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.processed_at >= datetime.now(tz=timezone.utc) - timedelta(days=30)
        ).scalar() or 0
        expiring_soon = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.end_date <= datetime.now(tz=timezone.utc) + timedelta(days=7)
        ).count()
        failed_payments = Payment.query.filter_by(status='failed').count()

        previous_start = datetime.now(tz=timezone.utc) - timedelta(days=60)
        previous_revenue = db.session.query(func.sum(Payment.amount)).filter(
            Payment.status == 'completed',
            Payment.processed_at.between(previous_start, previous_start + timedelta(days=30))
        ).scalar() or 0
        previous_subscribers = Subscription.query.filter(
            Subscription.status.in_(['active', 'trial']),
            Subscription.created_at <= previous_start
        ).count()
        previous_expiring = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.end_date <= previous_start + timedelta(days=7)
        ).count()
        previous_failed = Payment.query.filter(
            Payment.status == 'failed',
            Payment.processed_at <= previous_start
        ).count()

        subscription_metrics = {
            'total_change': ((num_subscribers - previous_subscribers) / previous_subscribers * 100) if previous_subscribers > 0 else 0,
            'revenue_change': ((revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0,
            'expiring_change': ((expiring_soon - previous_expiring) / previous_expiring * 100) if previous_expiring > 0 else 0,
            'failed_change': ((failed_payments - previous_failed) / previous_failed * 100) if previous_failed > 0 else 0
        }

        subscriptions = Subscription.query.order_by(Subscription.start_date.desc()).all()
        users = User.query.filter_by(role='athlete').all()
        plans = SubscriptionPlan.query.filter_by(is_active=True).order_by(SubscriptionPlan.sort_order).all()

        return render_template(
            'admin/subscription_management.html',
            num_subscribers=num_subscribers,
            revenue=revenue,
            expiring_soon=expiring_soon,
            failed_payments=failed_payments,
            subscription_metrics=subscription_metrics,
            subscriptions=subscriptions,
            users=users,
            plans=plans
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/membership_types', methods=['GET'])
@jwt_required()
def api_membership_types():
    """Fetch membership types data for chart"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            end_date = datetime.now(tz=timezone.utc)
            start_date = end_date - timedelta(days=30)

        membership_types = get_membership_types(start_date, end_date)
        return jsonify({"success": True, "membership_types": membership_types})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions', methods=['GET'])
@jwt_required()
def get_subscriptions():
    """Fetch all subscriptions with filters"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        status = request.args.get('status', '')
        plan = request.args.get('plan', '')
        query = Subscription.query

        if status:
            query = query.filter_by(status=status)
        if plan:
            query = query.join(SubscriptionPlan).filter(SubscriptionPlan.name.ilike(f'%{plan}%'))

        subscriptions = query.order_by(Subscription.start_date.desc()).all()
        subscription_data = [
            {
                'id': sub.id,
                'user': {
                    'name': sub.user.name if sub.user else 'Unknown',
                    'email': sub.user.email if sub.user else 'N/A',
                    'profile_image': sub.user.profile_image if sub.user else '/static/images/default.jpg',
                    'role': sub.user.role if sub.user else 'N/A',
                    'created_at': sub.user.created_at.strftime('%b %Y') if sub.user and sub.user.created_at else 'N/A',
                    'subscription_count': sub.user.subscriptions.count() if sub.user else 0
                },
                'plan_name': sub.plan.name if sub.plan else 'N/A',
                'price': float(sub.plan.price) if sub.plan else 0.0,
                'status': sub.status,
                'start_date': sub.start_date.strftime('%b %d, %Y') if sub.start_date else 'N/A',
                'end_date': sub.end_date.strftime('%b %d, %Y') if sub.end_date else 'N/A',
                'revenue': float(sub.total_paid),
                'usage_percentage': sub.usage_records.filter_by(feature='athletes').first().usage_percentage if sub.usage_records.filter_by(feature='athletes').first() else 0,
                'features': sub.plan.features if sub.plan else []
            } for sub in subscriptions
        ]

        return jsonify({"success": True, "subscriptions": subscription_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create a new subscription"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        user_id = data.get('user_id')
        plan_id = data.get('plan_id')
        start_date = data.get('start_date')
        billing_cycle = data.get('billing_cycle', 'monthly')
        trial_enabled = data.get('trial_enabled', False)
        trial_days = int(data.get('trial_days', 0)) if trial_enabled else 0
        auto_renew = data.get('auto_renew', True)
        notes = data.get('notes', '')

        # Convert string values to boolean
        if isinstance(trial_enabled, str):
            trial_enabled = trial_enabled.lower() in ('true', 'on', '1')
        if isinstance(auto_renew, str):
            auto_renew = auto_renew.lower() in ('true', 'on', '1')

        if not user_id or not plan_id or not start_date:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        user = User.query.get(user_id)
        plan = SubscriptionPlan.query.get(plan_id)
        if not user or not plan:
            return jsonify({"success": False, "error": "Invalid user or plan"}), 404

        start_date = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=30 * plan.duration_months)
        trial_end_date = start_date + timedelta(days=trial_days) if trial_enabled else None
        status = 'trial' if trial_enabled else 'active'

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
            trial_end_date=trial_end_date,
            auto_renew=auto_renew,
            billing_cycle=billing_cycle,
            status=status,
            next_billing_date=end_date if auto_renew else None,
            current_period_start=start_date,
            current_period_end=end_date,
            usage_data={'notes': notes}
        )

        usage_records = [
            SubscriptionUsage(
                subscription=subscription,
                feature='athletes',
                usage_count=0,
                usage_limit=plan.max_athletes,
                period_start=start_date,
                period_end=end_date
            ),
            SubscriptionUsage(
                subscription=subscription,
                feature='workouts',
                usage_count=0,
                usage_limit=plan.max_workouts,
                period_start=start_date,
                period_end=end_date
            ),
            SubscriptionUsage(
                subscription=subscription,
                feature='storage',
                usage_count=0,
                usage_limit=plan.storage_gb,
                period_start=start_date,
                period_end=end_date
            )
        ]

        db.session.add(subscription)
        db.session.add_all(usage_records)
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription created successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route('/api/subscriptions/<int:id>', methods=['GET'])
@jwt_required()
def get_subscription(id):
    """Fetch a single subscription's details"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        sub = Subscription.query.get(id)
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        payment_history = [
            {
                'date': p.processed_at.strftime('%b %d, %Y') if p.processed_at else 'N/A',
                'amount': float(p.amount),
                'method': f"{p.payment_method.brand} **** {p.payment_method.last_four}" if p.payment_method else 'N/A',
                'status': p.status,
                'invoice_url': f"/invoices/{p.id}" if p.provider_transaction_id else '#'
            } for p in sub.payments
        ]

        subscription_data = {
            'id': sub.id,
            'user': {
                'name': sub.user.name if sub.user else 'Unknown',
                'email': sub.user.email if sub.user else 'N/A',
                'profile_image': sub.user.profile_image if sub.user else '/static/images/default.jpg',
                'role': sub.user.role if sub.user else 'N/A',
                'created_at': sub.user.created_at.strftime('%b %Y') if sub.user and sub.user.created_at else 'N/A',
                'subscription_count': sub.user.subscriptions.count() if sub.user else 0
            },
            'plan_name': sub.plan.name if sub.plan else 'N/A',
            'price': float(sub.plan.price) if sub.plan else 0.0,
            'status': sub.status,
            'start_date': sub.start_date.strftime('%b %d, %Y') if sub.start_date else 'N/A',
            'end_date': sub.end_date.strftime('%b %d, %Y') if sub.end_date else 'N/A',
            'auto_renew': sub.auto_renew,
            'days_remaining': sub.days_remaining,
            'features': sub.plan.features if sub.plan else [],
            'athletes_used': sub.usage_records.filter_by(feature='athletes').first().usage_count if sub.usage_records.filter_by(feature='athletes').first() else 0,
            'athletes_limit': sub.plan.max_athletes if sub.plan else 0,
            'storage_used': sub.usage_records.filter_by(feature='storage').first().usage_count if sub.usage_records.filter_by(feature='storage').first() else 0,
            'storage_limit': sub.plan.storage_gb if sub.plan else 0,
            'revenue': float(sub.total_paid),
            'last_activity': sub.last_activity_at.strftime('%b %d, %Y %H:%M') if sub.last_activity_at else 'N/A',
            'login_count': sub.user.login_count if sub.user and hasattr(sub.user, 'login_count') else 0,
            'payment_history': payment_history
        }

        return jsonify({"success": True, "subscription": subscription_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/<int:id>/renew', methods=['POST'])
@jwt_required()
def renew_subscription(id):
    """Renew a subscription"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        sub = Subscription.query.get(id)
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        sub.extend_subscription()
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription renewed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/<int:id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(id):
    """Cancel a subscription"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        sub = Subscription.query.get(id)
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        sub.cancel_subscription(immediate=True)
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription canceled successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/<int:id>/convert', methods=['POST'])
@jwt_required()
def convert_trial(id):
    """Convert a trial subscription to paid"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        sub = Subscription.query.get(id)
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404
        if sub.status != 'trial':
            return jsonify({"success": False, "error": "Subscription is not in trial mode"}), 400

        sub.status = 'active'
        sub.trial_end_date = None
        sub.updated_at = datetime.now(tz=timezone.utc)
        db.session.commit()

        return jsonify({"success": True, "message": "Trial converted to paid subscription"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/bulk', methods=['POST'])
@jwt_required()
def bulk_actions():
    """Perform bulk actions on subscriptions"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data or 'ids' not in data or 'action' not in data:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        ids = data.get('ids', [])
        action = data.get('action')
        if not ids:
            return jsonify({"success": False, "error": "No subscriptions selected"}), 400

        subscriptions = Subscription.query.filter(Subscription.id.in_(ids)).all()
        if not subscriptions:
            return jsonify({"success": False, "error": "No valid subscriptions found"}), 404

        if action == 'extend':
            extend_days = int(data.get('extend_days', 30))
            months = extend_days // 30
            for sub in subscriptions:
                sub.extend_subscription(months=months)
        elif action == 'cancel':
            for sub in subscriptions:
                sub.cancel_subscription(immediate=True)
        elif action == 'change_plan':
            new_plan_id = data.get('new_plan_id')
            new_plan = SubscriptionPlan.query.get(new_plan_id)
            if not new_plan:
                return jsonify({"success": False, "error": "Invalid plan ID"}), 404
            for sub in subscriptions:
                sub.plan_id = new_plan_id
                sub.end_date = datetime.now(tz=timezone.utc) + timedelta(days=30 * new_plan.duration_months)
                sub.current_period_end = sub.end_date
        elif action == 'send_notification':
            message = data.get('message')
            if not message:
                return jsonify({"success": False, "error": "Message is required for notification"}), 400
            # Placeholder for notification logic
            for sub in subscriptions:
                pass
        else:
            return jsonify({"success": False, "error": "Invalid action"}), 400

        db.session.commit()
        return jsonify({"success": True, "message": f"Bulk action {action} executed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans', methods=['GET'])
@jwt_required()
def get_plans():
    """Fetch all subscription plans"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plans = SubscriptionPlan.query.order_by(SubscriptionPlan.sort_order).all()
        plan_data = [
            {
                'id': plan.id,
                'name': plan.name,
                'price': float(plan.price),
                'max_athletes': plan.max_athletes,
                'max_workouts': plan.max_workouts,
                'storage_gb': plan.storage_gb,
                'features': plan.features,
                'duration_months': plan.duration_months,
                'is_active': plan.is_active
            } for plan in plans
        ]
        return jsonify({"success": True, "plans": plan_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans', methods=['POST'])
@jwt_required()
def create_plan():
    """Create a new subscription plan"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        name = data.get('name')
        price = data.get('price')
        max_athletes = data.get('max_athletes')
        max_workouts = data.get('max_workouts')
        storage_gb = data.get('storage_gb')
        features = data.get('features', [])
        duration_months = data.get('duration_months', 1)
        is_active = data.get('is_active', True)

        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true' or is_active == 'on'

        if not name or price is None or max_athletes is None or max_workouts is None or storage_gb is None:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        plan = SubscriptionPlan(
            name=name,
            price=float(price),
            max_athletes=int(max_athletes),
            max_workouts=int(max_workouts),
            storage_gb=int(storage_gb),
            features=features,
            duration_months=int(duration_months),
            is_active=is_active,
            sort_order=SubscriptionPlan.query.count() + 1
        )

        db.session.add(plan)
        db.session.commit()

        return jsonify({"success": True, "message": "Plan created successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans/<int:id>', methods=['GET'])
@jwt_required()
def get_plan(id):
    """Fetch a single subscription plan"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = SubscriptionPlan.query.get(id)
        if not plan:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        plan_data = {
            'id': plan.id,
            'name': plan.name,
            'price': float(plan.price),
            'max_athletes': plan.max_athletes,
            'max_workouts': plan.max_workouts,
            'storage_gb': plan.storage_gb,
            'features': plan.features,
            'duration_months': plan.duration_months,
            'is_active': plan.is_active
        }
        return jsonify({"success": True, "plan": plan_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans/<int:id>', methods=['PUT'])
@jwt_required()
def update_plan(id):
    """Update a subscription plan"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = SubscriptionPlan.query.get(id)
        if not plan:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        plan.name = data.get('name', plan.name)
        plan.price = float(data.get('price', plan.price))
        plan.max_athletes = int(data.get('max_athletes', plan.max_athletes))
        plan.max_workouts = int(data.get('max_workouts', plan.max_workouts))
        plan.storage_gb = int(data.get('storage_gb', plan.storage_gb))
        plan.features = data.get('features', plan.features)
        plan.duration_months = int(data.get('duration_months', plan.duration_months))
        is_active = data.get('is_active', plan.is_active)
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true' or is_active == 'on'
        plan.is_active = is_active

        db.session.commit()
        return jsonify({"success": True, "message": "Plan updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_plan(id):
    """Delete a subscription plan"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plan = SubscriptionPlan.query.get(id)
        if not plan:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        if Subscription.query.filter_by(plan_id=id).count() > 0:
            return jsonify({"success": False, "error": "Cannot delete plan with active subscriptions"}), 400

        db.session.delete(plan)
        db.session.commit()
        return jsonify({"success": True, "message": "Plan deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500