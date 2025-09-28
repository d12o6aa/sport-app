from flask import Blueprint, jsonify, render_template, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.models.subscription import Subscription
from app.models.subscription_plans import SubscriptionPlan
from app.models.payments import Payment
from app.models.payment_methods import PaymentMethod
from app.models.subscription_usage import SubscriptionUsage
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_, or_
import logging

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
            "Enterprise": "#ff2d55",
            "Pro": "#6c757d",
            "Starter": "#20c997"
        }
        
        # Get plans with subscription counts
        plans_data = db.session.query(
            SubscriptionPlan.name,
            func.count(Subscription.id).label('count')
        ).outerjoin(
            Subscription, and_(
                SubscriptionPlan.id == Subscription.plan_id,
                Subscription.created_at.between(start_date, end_date),
                Subscription.status.in_(['active', 'trial'])
            )
        ).filter(
            SubscriptionPlan.is_active == True
        ).group_by(SubscriptionPlan.id, SubscriptionPlan.name).all()
        
        membership_types = []
        for plan_name, count in plans_data:
            membership_types.append({
                "name": plan_name,
                "count": count or 0,
                "color": color_map.get(plan_name, "#6c757d")
            })
        
        # If no data, create sample data
        if not membership_types:
            membership_types = [
                {"name": "Basic", "count": 0, "color": "#ff771d"},
                {"name": "Premium", "count": 0, "color": "#4154f1"},
                {"name": "Enterprise", "count": 0, "color": "#ff2d55"}
            ]
        
        return membership_types
        
    except Exception as e:
        logging.error(f"Error in get_membership_types: {e}")
        return [
            {"name": "Basic", "count": 0, "color": "#ff771d"},
            {"name": "Premium", "count": 0, "color": "#4154f1"}
        ]

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
        # Calculate current metrics
        now = datetime.now(tz=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)
        
        # Current period metrics
        num_subscribers = Subscription.query.filter(
            Subscription.status.in_(['active', 'trial'])
        ).count()
        
        revenue = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.status == 'completed',
            Payment.processed_at >= thirty_days_ago
        ).scalar() or 0
        
        expiring_soon = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.end_date <= now + timedelta(days=7),
            Subscription.end_date > now
        ).count()
        
        failed_payments = Payment.query.filter(
            Payment.status == 'failed',
            Payment.created_at >= thirty_days_ago
        ).count()

        # Previous period metrics for comparison
        previous_subscribers = Subscription.query.filter(
            Subscription.status.in_(['active', 'trial']),
            Subscription.created_at <= sixty_days_ago,
            Subscription.created_at > sixty_days_ago - timedelta(days=30)
        ).count()
        
        previous_revenue = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter(
            Payment.status == 'completed',
            Payment.processed_at.between(sixty_days_ago, thirty_days_ago)
        ).scalar() or 0
        
        previous_expiring = Subscription.query.filter(
            Subscription.status == 'active',
            Subscription.end_date <= sixty_days_ago + timedelta(days=7),
            Subscription.end_date > sixty_days_ago,
            Subscription.created_at <= sixty_days_ago
        ).count()
        
        previous_failed = Payment.query.filter(
            Payment.status == 'failed',
            Payment.created_at.between(sixty_days_ago, thirty_days_ago)
        ).count()

        # Calculate percentage changes
        def calculate_change(current, previous):
            if previous > 0:
                return round(((current - previous) / previous * 100), 1)
            return 100 if current > 0 else 0

        subscription_metrics = {
            'total_change': calculate_change(num_subscribers, previous_subscribers),
            'revenue_change': calculate_change(float(revenue), float(previous_revenue)),
            'expiring_change': calculate_change(expiring_soon, previous_expiring),
            'failed_change': calculate_change(failed_payments, previous_failed)
        }

        # Get subscription data with joins
        subscriptions = db.session.query(Subscription).join(
            User, Subscription.user_id == User.id
        ).outerjoin(
            SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id
        ).order_by(Subscription.created_at.desc()).limit(100).all()
        
        # Get users and plans for dropdowns
        users = User.query.filter(
            User.role.in_(['athlete', 'coach']),
            User.is_deleted == False
        ).order_by(User.name).all()
        
        plans = SubscriptionPlan.query.filter_by(
            is_active=True
        ).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.name).all()

        # Create template filter for format_change
        from flask import current_app
        current_app.jinja_env.filters['format_change'] = format_change

        return render_template(
            'admin/subscription_management.html',
            num_subscribers=num_subscribers,
            revenue=float(revenue),
            expiring_soon=expiring_soon,
            failed_payments=failed_payments,
            subscription_metrics=subscription_metrics,
            subscriptions=subscriptions,
            users=users,
            plans=plans,
            format_change=format_change
        )
    except Exception as e:
        logging.error(f"Error in subscriptions route: {e}")
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
                # Make end_date end of day
                end_date = end_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                return jsonify({"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}), 400
        else:
            end_date = datetime.now(tz=timezone.utc)
            start_date = end_date - timedelta(days=30)

        membership_types = get_membership_types(start_date, end_date)
        
        return jsonify({
            "success": True, 
            "membership_types": membership_types,
            "date_range": {
                "start": start_date.strftime('%Y-%m-%d'),
                "end": end_date.strftime('%Y-%m-%d')
            }
        })
    except Exception as e:
        logging.error(f"Error in api_membership_types: {e}")
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
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        # Build query with joins
        query = db.session.query(Subscription).join(
            User, Subscription.user_id == User.id
        ).outerjoin(
            SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id
        )

        if status:
            query = query.filter(Subscription.status == status)
        if plan:
            query = query.filter(SubscriptionPlan.name.ilike(f'%{plan}%'))

        # Get paginated results
        subscriptions = query.order_by(Subscription.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        subscription_data = []
        for sub in subscriptions.items:
            # Get usage data
            usage_records = sub.usage_records.all()
            athletes_usage = next((u for u in usage_records if u.feature == 'athletes'), None)
            
            subscription_data.append({
                'id': sub.id,
                'user': {
                    'name': sub.user.name if sub.user else 'Unknown',
                    'email': sub.user.email if sub.user else 'N/A',
                    'profile_image': sub.user.profile_image_url if sub.user else '/static/images/default.jpg',
                    'role': sub.user.role if sub.user else 'N/A',
                    'created_at': sub.user.created_at.strftime('%b %Y') if sub.user and sub.user.created_at else 'N/A',
                    'subscription_count': sub.user.subscriptions.count() if sub.user else 0
                },
                'plan_name': sub.plan.name if sub.plan else 'No Plan',
                'price': float(sub.plan.price) if sub.plan else 0.0,
                'status': sub.status,
                'start_date': sub.start_date.strftime('%b %d, %Y') if sub.start_date else 'N/A',
                'end_date': sub.end_date.strftime('%b %d, %Y') if sub.end_date else 'N/A',
                'revenue': sub.total_paid,
                'usage_percentage': athletes_usage.usage_percentage if athletes_usage else 0,
                'features': sub.plan.features if sub.plan else []
            })

        return jsonify({
            "success": True, 
            "subscriptions": subscription_data,
            "pagination": {
                "page": subscriptions.page,
                "pages": subscriptions.pages,
                "per_page": subscriptions.per_page,
                "total": subscriptions.total
            }
        })
    except Exception as e:
        logging.error(f"Error in get_subscriptions: {e}")
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
        start_date_str = data.get('start_date')
        billing_cycle = data.get('billing_cycle', 'monthly')
        trial_enabled = data.get('trial_enabled', False)
        trial_days = int(data.get('trial_days', 14)) if trial_enabled else 0
        auto_renew = data.get('auto_renew', True)
        notes = data.get('notes', '')

        # Convert boolean values
        if isinstance(trial_enabled, str):
            trial_enabled = trial_enabled.lower() in ('true', 'on', '1')
        if isinstance(auto_renew, str):
            auto_renew = auto_renew.lower() in ('true', 'on', '1')

        if not user_id or not plan_id or not start_date_str:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        user = User.query.get(user_id)
        plan = SubscriptionPlan.query.get(plan_id)
        if not user or not plan:
            return jsonify({"success": False, "error": "Invalid user or plan"}), 404

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        end_date = start_date + timedelta(days=30 * plan.duration_months)
        trial_end_date = start_date + timedelta(days=trial_days) if trial_enabled else None
        status = 'trial' if trial_enabled else 'active'

        # Check for existing active subscription
        existing_sub = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        if existing_sub:
            return jsonify({
                "success": False, 
                "error": f"User already has an active subscription (#{existing_sub.id})"
            }), 400

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
            usage_data={'notes': notes} if notes else None
        )

        db.session.add(subscription)
        db.session.flush()  # Get the ID

        # Create usage records
        usage_records = [
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='athletes',
                usage_count=0,
                usage_limit=plan.max_athletes,
                period_start=start_date,
                period_end=end_date
            ),
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='workouts',
                usage_count=0,
                usage_limit=plan.max_workouts,
                period_start=start_date,
                period_end=end_date
            ),
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='storage',
                usage_count=0,
                usage_limit=plan.storage_gb,
                period_start=start_date,
                period_end=end_date
            )
        ]

        db.session.add_all(usage_records)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Subscription created successfully",
            "subscription_id": subscription.id
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/<int:id>', methods=['GET'])
@jwt_required()
def get_subscription(id):
    """Fetch a single subscription's details"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        sub = db.session.query(Subscription).join(
            User, Subscription.user_id == User.id
        ).outerjoin(
            SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id
        ).filter(Subscription.id == id).first()
        
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        # Get payment history
        payment_history = []
        for p in sub.payments.order_by(Payment.created_at.desc()).all():
            payment_history.append({
                'date': p.processed_at.strftime('%b %d, %Y') if p.processed_at else p.created_at.strftime('%b %d, %Y'),
                'amount': float(p.amount),
                'method': p.payment_method.display_name() if p.payment_method else 'N/A',
                'status': p.status,
                'invoice_url': f"/admin/invoices/{p.id}" if p.provider_transaction_id else '#'
            })

        # Get usage records
        usage_records = sub.usage_records.all()
        athletes_usage = next((u for u in usage_records if u.feature == 'athletes'), None)
        storage_usage = next((u for u in usage_records if u.feature == 'storage'), None)

        subscription_data = {
            'id': sub.id,
            'user': {
                'name': sub.user.name if sub.user else 'Unknown',
                'email': sub.user.email if sub.user else 'N/A',
                'profile_image': sub.user.profile_image_url if sub.user else '/static/images/default.jpg',
                'role': sub.user.role if sub.user else 'N/A',
                'created_at': sub.user.created_at.strftime('%b %Y') if sub.user and sub.user.created_at else 'N/A',
                'subscription_count': sub.user.subscriptions.count() if sub.user else 0
            },
            'plan_name': sub.plan.name if sub.plan else 'No Plan',
            'price': float(sub.plan.price) if sub.plan else 0.0,
            'status': sub.status,
            'start_date': sub.start_date.strftime('%b %d, %Y') if sub.start_date else 'N/A',
            'end_date': sub.end_date.strftime('%b %d, %Y') if sub.end_date else 'N/A',
            'auto_renew': sub.auto_renew,
            'days_remaining': sub.days_remaining,
            'features': sub.plan.features if sub.plan and sub.plan.features else [],
            'athletes_used': athletes_usage.usage_count if athletes_usage else 0,
            'athletes_limit': sub.plan.max_athletes if sub.plan else 0,
            'storage_used': storage_usage.usage_count if storage_usage else 0,
            'storage_limit': sub.plan.storage_gb if sub.plan else 0,
            'revenue': sub.total_paid,
            'last_activity': sub.last_activity_at.strftime('%b %d, %Y %H:%M') if sub.last_activity_at else 'Never',
            'login_count': getattr(sub.user, 'login_count', 0) if sub.user else 0,
            'payment_history': payment_history
        }

        return jsonify({"success": True, "subscription": subscription_data})
    except Exception as e:
        logging.error(f"Error getting subscription {id}: {e}")
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

        return jsonify({
            "success": True, 
            "message": "Subscription renewed successfully",
            "new_end_date": sub.end_date.strftime('%b %d, %Y') if sub.end_date else None
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error renewing subscription {id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/<int:id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(id):
    """Cancel a subscription"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Cancelled by admin')
        immediate = data.get('immediate', True)
        
        sub = Subscription.query.get(id)
        if not sub:
            return jsonify({"success": False, "error": "Subscription not found"}), 404

        sub.cancel_subscription(reason=reason, immediate=immediate)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Subscription cancelled successfully"
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cancelling subscription {id}: {e}")
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

        return jsonify({
            "success": True, 
            "message": "Trial converted to paid subscription successfully"
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error converting trial {id}: {e}")
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

        processed_count = 0
        
        if action == 'extend':
            extend_days = int(data.get('extend_days', 30))
            months = max(1, extend_days // 30)
            for sub in subscriptions:
                sub.extend_subscription(months=months)
                processed_count += 1
                
        elif action == 'cancel':
            reason = data.get('reason', 'Bulk cancellation by admin')
            for sub in subscriptions:
                if sub.status in ['active', 'trial']:
                    sub.cancel_subscription(reason=reason, immediate=True)
                    processed_count += 1
                    
        elif action == 'change_plan':
            new_plan_id = data.get('new_plan_id')
            new_plan = SubscriptionPlan.query.get(new_plan_id)
            if not new_plan:
                return jsonify({"success": False, "error": "Invalid plan ID"}), 404
            for sub in subscriptions:
                sub.plan_id = new_plan_id
                sub.end_date = datetime.now(tz=timezone.utc) + timedelta(days=30 * new_plan.duration_months)
                sub.current_period_end = sub.end_date
                processed_count += 1
                
        elif action == 'send_notification':
            message = data.get('message')
            if not message:
                return jsonify({"success": False, "error": "Message is required for notification"}), 400
            # TODO: Implement notification logic
            processed_count = len(subscriptions)
            
        else:
            return jsonify({"success": False, "error": "Invalid action"}), 400

        db.session.commit()
        
        return jsonify({
            "success": True, 
            "message": f"Bulk action '{action}' executed successfully on {processed_count} subscription(s)"
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in bulk actions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/plans', methods=['GET'])
@jwt_required()
def get_plans():
    """Fetch all subscription plans"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plans = SubscriptionPlan.query.order_by(
            SubscriptionPlan.sort_order, 
            SubscriptionPlan.name
        ).all()
        
        plan_data = []
        for plan in plans:
            plan_data.append({
                'id': plan.id,
                'name': plan.name,
                'description': plan.description,
                'price': float(plan.price),
                'max_athletes': plan.max_athletes,
                'max_workouts': plan.max_workouts,
                'storage_gb': plan.storage_gb,
                'features': plan.features or [],
                'duration_months': plan.duration_months,
                'is_active': plan.is_active,
                'sort_order': plan.sort_order,
                'active_subscriptions': plan.active_subscriptions_count
            })
            
        return jsonify({"success": True, "plans": plan_data})
    except Exception as e:
        logging.error(f"Error getting plans: {e}")
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

        # Validate required fields
        required_fields = ['name', 'price', 'max_athletes', 'max_workouts', 'storage_gb']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        # Process features
        features = data.get('features', [])
        if isinstance(features, str):
            features = [f.strip() for f in features.split('\n') if f.strip()]

        # Handle boolean conversion
        is_active = data.get('is_active', True)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ('true', 'on', '1')

        plan = SubscriptionPlan(
            name=data['name'].strip(),
            description=data.get('description', '').strip(),
            price=float(data['price']),
            max_athletes=int(data['max_athletes']),
            max_workouts=int(data['max_workouts']),
            storage_gb=int(data['storage_gb']),
            features=features,
            duration_months=int(data.get('duration_months', 1)),
            is_active=is_active,
            sort_order=SubscriptionPlan.query.count() + 1,
            priority_support=data.get('priority_support', False),
            analytics_access=data.get('analytics_access', False),
            custom_branding=data.get('custom_branding', False),
            api_access=data.get('api_access', False)
        )

        db.session.add(plan)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Plan created successfully",
            "plan_id": plan.id
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating plan: {e}")
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

        plan_data = plan.to_dict()
        return jsonify({"success": True, "plan": plan_data})
    except Exception as e:
        logging.error(f"Error getting plan {id}: {e}")
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

        # Update fields
        plan.name = data.get('name', plan.name).strip()
        plan.description = data.get('description', plan.description).strip()
        plan.price = float(data.get('price', plan.price))
        plan.max_athletes = int(data.get('max_athletes', plan.max_athletes))
        plan.max_workouts = int(data.get('max_workouts', plan.max_workouts))
        plan.storage_gb = int(data.get('storage_gb', plan.storage_gb))
        plan.duration_months = int(data.get('duration_months', plan.duration_months))
        
        # Process features
        features = data.get('features', plan.features)
        if isinstance(features, str):
            features = [f.strip() for f in features.split('\n') if f.strip()]
        plan.features = features
        
        # Handle boolean fields
        is_active = data.get('is_active', plan.is_active)
        if isinstance(is_active, str):
            is_active = is_active.lower() in ('true', 'on', '1')
        plan.is_active = is_active
        
        plan.updated_at = datetime.utcnow()

        db.session.commit()
        return jsonify({"success": True, "message": "Plan updated successfully"})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating plan {id}: {e}")
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

        # Check if plan has active subscriptions
        active_subscriptions = Subscription.query.filter(
            Subscription.plan_id == id,
            Subscription.status.in_(['active', 'trial'])
        ).count()
        
        if active_subscriptions > 0:
            return jsonify({
                "success": False, 
                "error": f"Cannot delete plan with {active_subscriptions} active subscription(s). Cancel or change subscriptions first."
            }), 400

        db.session.delete(plan)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Plan deleted successfully"})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting plan {id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@admin_bp.route('/api/subscriptions/export', methods=['GET'])
@jwt_required()
def export_subscriptions():
    """Export subscriptions data as CSV"""
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        import csv
        import io
        from flask import make_response
        
        status = request.args.get('status', '')
        plan = request.args.get('plan', '')
        
        # Build query
        query = db.session.query(Subscription).join(
            User, Subscription.user_id == User.id
        ).outerjoin(
            SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id
        )
        
        if status:
            query = query.filter(Subscription.status == status)
        if plan:
            query = query.filter(SubscriptionPlan.name.ilike(f'%{plan}%'))
        
        subscriptions = query.order_by(Subscription.created_at.desc()).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'User Name', 'User Email', 'Plan', 'Status', 
            'Start Date', 'End Date', 'Revenue', 'Auto Renew', 'Created At'
        ])
        
        # Write data
        for sub in subscriptions:
            writer.writerow([
                sub.id,
                sub.user.name if sub.user else 'Unknown',
                sub.user.email if sub.user else 'N/A',
                sub.plan.name if sub.plan else 'No Plan',
                sub.status,
                sub.start_date.strftime('%Y-%m-%d') if sub.start_date else '',
                sub.end_date.strftime('%Y-%m-%d') if sub.end_date else '',
                float(sub.total_paid),
                'Yes' if sub.auto_renew else 'No',
                sub.created_at.strftime('%Y-%m-%d %H:%M:%S') if sub.created_at else ''
            ])
        
        output.seek(0)
        
        # Create response
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=subscriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response.headers["Content-type"] = "text/csv"
        
        return response
        
    except Exception as e:
        logging.error(f"Error exporting subscriptions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500