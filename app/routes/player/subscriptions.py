# app/views/athlete/subscriptions.py
from flask import Blueprint, jsonify, render_template, request, redirect, url_for
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
import requests
import hashlib
import hmac

from . import athlete_bp  # Assuming athlete_bp is defined in __init__.py of the athlete package

def is_athlete_or_coach(identity):
    """Check if the user is athlete or coach"""
    user = User.query.filter_by(id=identity).first()
    return user and user.role in ['athlete', 'coach']

def get_subscription_metrics(user_id):
    """Generate subscription metrics for athlete/coach"""
    try:
        now = datetime.now(tz=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        # Current subscription
        current_subscription = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        # Total subscriptions count
        total_subscriptions = Subscription.query.filter_by(user_id=user_id).count()
        
        # Total spent
        total_spent = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(Subscription).filter(
            Subscription.user_id == user_id,
            Payment.status == 'completed'
        ).scalar() or 0
        
        # Days remaining
        days_remaining = 0
        if current_subscription and current_subscription.end_date:
            delta = current_subscription.end_date - now
            days_remaining = max(0, delta.days)
        
        # Recent payments (last 30 days)
        recent_payments = Payment.query.join(Subscription).filter(
            Subscription.user_id == user_id,
            Payment.created_at >= thirty_days_ago,
            Payment.status == 'completed'
        ).count()
        
        return {
            'current_subscription': current_subscription,
            'total_subscriptions': total_subscriptions,
            'total_spent': float(total_spent),
            'days_remaining': days_remaining,
            'recent_payments': recent_payments,
            'is_active': current_subscription and current_subscription.status in ['active', 'trial']
        }
        
    except Exception as e:
        logging.error(f"Error in get_subscription_metrics: {e}")
        return {
            'current_subscription': None,
            'total_subscriptions': 0,
            'total_spent': 0.0,
            'days_remaining': 0,
            'recent_payments': 0,
            'is_active': False
        }

@athlete_bp.route('/subscriptions', methods=['GET'])
@jwt_required()
def subscriptions():
    """Render the athlete subscription management page"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        user = User.query.get(identity)
        
        # Get subscription metrics
        metrics = get_subscription_metrics(identity)
        
        # Get all available plans
        available_plans = SubscriptionPlan.query.filter_by(
            is_active=True
        ).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.price).all()
        
        # Get subscription history
        subscription_history = Subscription.query.filter_by(
            user_id=identity
        ).order_by(Subscription.created_at.desc()).limit(10).all()
        
        # Get usage data
        usage_data = []
        if metrics['current_subscription']:
            usage_records = metrics['current_subscription'].usage_records.all()
            for usage in usage_records:
                usage_data.append({
                    'feature': usage.feature,
                    'used': usage.usage_count,
                    'limit': usage.usage_limit,
                    'percentage': usage.usage_percentage
                })
        
        # Get payment methods
        payment_methods = PaymentMethod.query.filter_by(
            user_id=identity,
            is_active=True
        ).all()
        
        return render_template(
            'athlete/subscription_management.html',
            user=user,
            current_subscription=metrics['current_subscription'],
            total_subscriptions=metrics['total_subscriptions'],
            total_spent=metrics['total_spent'],
            days_remaining=metrics['days_remaining'],
            recent_payments=metrics['recent_payments'],
            is_active_subscription=metrics['is_active'],
            available_plans=available_plans,
            subscription_history=subscription_history,
            usage_data=usage_data,
            payment_methods=payment_methods
        )
        
    except Exception as e:
        logging.error(f"Error in subscriptions route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/subscription_dashboard', methods=['GET'])
@jwt_required()
def api_subscription_dashboard():
    """Fetch subscription dashboard data"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        metrics = get_subscription_metrics(identity)
        
        dashboard_data = {
            'has_active_subscription': metrics['is_active'],
            'current_plan': {
                'id': metrics['current_subscription'].plan_id if metrics['current_subscription'] else None,
                'name': metrics['current_subscription'].plan.name if metrics['current_subscription'] and metrics['current_subscription'].plan else None,
                'price': float(metrics['current_subscription'].plan.price) if metrics['current_subscription'] and metrics['current_subscription'].plan else 0,
                'status': metrics['current_subscription'].status if metrics['current_subscription'] else None
            },
            'stats': {
                'total_subscriptions': metrics['total_subscriptions'],
                'total_spent': metrics['total_spent'],
                'days_remaining': metrics['days_remaining'],
                'recent_payments': metrics['recent_payments']
            }
        }
        
        # Get usage data
        if metrics['current_subscription']:
            usage_records = metrics['current_subscription'].usage_records.all()
            dashboard_data['usage'] = []
            for usage in usage_records:
                dashboard_data['usage'].append({
                    'feature': usage.feature,
                    'used': usage.usage_count,
                    'limit': usage.usage_limit,
                    'percentage': usage.usage_percentage,
                    'is_over_limit': usage.is_over_limit
                })
        else:
            dashboard_data['usage'] = []
        
        return jsonify({
            "success": True,
            "dashboard": dashboard_data
        })
        
    except Exception as e:
        logging.error(f"Error in api_subscription_dashboard: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/available_plans', methods=['GET'])
@jwt_required()
def get_available_plans():
    """Fetch available subscription plans"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        plans = SubscriptionPlan.query.filter_by(
            is_active=True
        ).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.price).all()
        
        # Get current subscription to compare
        current_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        current_plan_id = current_subscription.plan_id if current_subscription else None
        current_price = float(current_subscription.plan.price) if current_subscription and current_subscription.plan else 0
        
        plan_data = []
        for plan in plans:
            plan_info = {
                'id': plan.id,
                'name': plan.name,
                'description': plan.description,
                'price': float(plan.price),
                'duration_months': plan.duration_months,
                'features': plan.features or [],
                'max_athletes': plan.max_athletes,
                'max_workouts': plan.max_workouts,
                'storage_gb': plan.storage_gb,
                'is_current': plan.id == current_plan_id,
                'can_upgrade': current_subscription is None or plan.price > current_price,
                'can_downgrade': current_subscription is not None and plan.price < current_price,
                'active_subscriptions': plan.active_subscriptions_count
            }
            plan_data.append(plan_info)
        
        return jsonify({
            "success": True,
            "plans": plan_data,
            "current_plan_id": current_plan_id
        })
        
    except Exception as e:
        logging.error(f"Error getting available plans: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/subscribe', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create a new subscription"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payment_method = data.get('payment_method', 'card')
        auto_renew = data.get('auto_renew', True)
        trial_enabled = data.get('trial_enabled', False)

        if not plan_id:
            return jsonify({"success": False, "error": "Plan ID is required"}), 400

        # Check if user already has active subscription
        existing_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        if existing_subscription:
            return jsonify({
                "success": False,
                "error": "You already have an active subscription. Please cancel it first or upgrade your plan."
            }), 400

        # Get plan details
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan or not plan.is_active:
            return jsonify({"success": False, "error": "Invalid or inactive plan"}), 404

        # Calculate pricing and dates
        base_price = float(plan.price)
        final_price = base_price
        duration_days = 30 * plan.duration_months
        
        if billing_cycle == 'yearly':
            final_price = base_price * 12 * 0.8  # 20% discount
            duration_days = 365
        elif billing_cycle == 'quarterly':
            final_price = base_price * 3 * 0.9   # 10% discount
            duration_days = 90

        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=duration_days)
        trial_end_date = start_date + timedelta(days=14) if trial_enabled else None
        status = 'trial' if trial_enabled else 'pending'

        # Create subscription
        subscription = Subscription(
            user_id=identity,
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
            usage_data={
                'created_method': 'user_subscription',
                'payment_method': payment_method,
                'billing_cycle': billing_cycle
            }
        )

        db.session.add(subscription)
        db.session.flush()  # Get the ID

        # Create payment record (skip payment for trial)
        if not trial_enabled:
            payment = Payment(
                subscription_id=subscription.id,
                amount=final_price,
                currency='USD',
                status='pending',
                provider='paymob',  # Your payment provider
                extra_data={
                    'billing_cycle': billing_cycle,
                    'payment_method': payment_method,
                    'user_initiated': True
                }
            )

            db.session.add(payment)
            db.session.flush()

            # Process payment
            payment_result = process_payment_integration(payment, data)
            
            if payment_result['success']:
                subscription.status = 'active'
                payment.status = 'completed'
                payment.processed_at = datetime.now(timezone.utc)
                payment.provider_transaction_id = payment_result.get('transaction_id')
                
                # Create usage records
                create_usage_records(subscription)
                
                db.session.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Subscription created successfully!",
                    "subscription_id": subscription.id,
                    "payment_url": payment_result.get('payment_url')
                })
            else:
                subscription.status = 'canceled'
                payment.status = 'failed'
                payment.failure_reason = payment_result.get('error', 'Payment processing failed')
                
                db.session.commit()
                
                return jsonify({
                    "success": False,
                    "error": f"Payment failed: {payment_result.get('error', 'Unknown error')}"
                }), 400
        else:
            # Trial subscription - no payment needed
            subscription.status = 'trial'
            create_usage_records(subscription)
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Trial subscription created successfully!",
                "subscription_id": subscription.id,
                "trial_days": 14
            })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def process_payment_integration(payment, payment_data):
    """Process payment through payment gateway integration"""
    try:
        # Paymob Integration Example
        PAYMOB_API_KEY = "your_paymob_api_key_here"
        PAYMOB_INTEGRATION_ID = "your_integration_id_here"
        
        payment_method = payment_data.get('payment_method', 'card')
        
        if payment_method == 'card':
            # Step 1: Authentication
            auth_response = requests.post(
                "https://accept.paymob.com/api/auth/tokens",
                json={"api_key": PAYMOB_API_KEY},
                timeout=30
            )
            
            if not auth_response.ok:
                return {"success": False, "error": "Payment gateway authentication failed"}
            
            auth_token = auth_response.json().get("token")
            
            # Step 2: Create Order
            order_data = {
                "auth_token": auth_token,
                "delivery_needed": "false",
                "amount_cents": int(float(payment.amount) * 100),
                "currency": payment.currency,
                "items": [{
                    "name": f"Subscription - {payment.subscription.plan.name}",
                    "amount_cents": int(float(payment.amount) * 100),
                    "description": f"Subscription for user {payment.subscription.user.email}",
                    "quantity": "1"
                }]
            }
            
            order_response = requests.post(
                "https://accept.paymob.com/api/ecommerce/orders",
                json=order_data,
                timeout=30
            )
            
            if not order_response.ok:
                return {"success": False, "error": "Failed to create payment order"}
            
            order_id = order_response.json().get("id")
            
            # Step 3: Payment Key
            payment_key_data = {
                "auth_token": auth_token,
                "amount_cents": int(float(payment.amount) * 100),
                "expiration": 3600,
                "order_id": order_id,
                "billing_data": {
                    "apartment": "NA",
                    "email": payment.subscription.user.email,
                    "floor": "NA",
                    "first_name": payment.subscription.user.name.split()[0] if payment.subscription.user.name else "User",
                    "street": "NA",
                    "building": "NA",
                    "phone_number": "+201000000000",
                    "shipping_method": "NA",
                    "postal_code": "NA",
                    "city": "Cairo",
                    "country": "EG",
                    "last_name": payment.subscription.user.name.split()[-1] if len(payment.subscription.user.name.split()) > 1 else "User",
                    "state": "Cairo"
                },
                "currency": payment.currency,
                "integration_id": PAYMOB_INTEGRATION_ID,
                "lock_order_when_paid": "false"
            }
            
            payment_key_response = requests.post(
                "https://accept.paymob.com/api/acceptance/payment_keys",
                json=payment_key_data,
                timeout=30
            )
            
            if not payment_key_response.ok:
                return {"success": False, "error": "Failed to generate payment key"}
            
            payment_key = payment_key_response.json().get("token")
            
            return {
                "success": True,
                "transaction_id": f"ord_{order_id}",
                "payment_key": payment_key,
                "payment_url": f"https://accept.paymob.com/api/acceptance/iframes/your_iframe_id?payment_token={payment_key}",
                "order_id": order_id
            }
            
        elif payment_method == 'paypal':
            # PayPal integration would go here
            return {
                "success": True,
                "transaction_id": f"pp_{payment.id}_{int(datetime.now().timestamp())}",
                "payment_url": f"/payment/paypal/{payment.id}"
            }
        
        else:
            return {"success": False, "error": "Unsupported payment method"}
            
    except requests.RequestException as e:
        logging.error(f"Payment gateway request error: {e}")
        return {"success": False, "error": "Payment gateway connection failed"}
    except Exception as e:
        logging.error(f"Payment processing error: {e}")
        return {"success": False, "error": "Payment processing failed"}

def create_usage_records(subscription):
    """Create usage tracking records for subscription"""
    try:
        plan = subscription.plan
        
        usage_records = [
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='athletes',
                usage_count=0,
                usage_limit=plan.max_athletes,
                period_start=subscription.start_date,
                period_end=subscription.end_date
            ),
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='workouts',
                usage_count=0,
                usage_limit=plan.max_workouts,
                period_start=subscription.start_date,
                period_end=subscription.end_date
            ),
            SubscriptionUsage(
                subscription_id=subscription.id,
                feature='storage',
                usage_count=0,
                usage_limit=plan.storage_gb,
                period_start=subscription.start_date,
                period_end=subscription.end_date
            )
        ]

        db.session.add_all(usage_records)
        
    except Exception as e:
        logging.error(f"Error creating usage records: {e}")
        raise

@athlete_bp.route('/api/cancel_subscription', methods=['POST'])
@jwt_required()
def cancel_subscription():
    """Cancel current subscription"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'User requested cancellation')
        immediate = data.get('immediate', False)

        # Get current subscription
        subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not subscription:
            return jsonify({"success": False, "error": "No active subscription found"}), 404

        # Cancel subscription using the model method
        subscription.cancel_subscription(reason=reason, immediate=immediate)
        db.session.commit()

        message = "Subscription cancelled successfully" if immediate else "Subscription will be cancelled at the end of current period"

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cancelling subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/upgrade_plan', methods=['POST'])
@jwt_required()
def upgrade_plan():
    """Upgrade subscription to a higher plan"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        new_plan_id = data.get('plan_id')
        if not new_plan_id:
            return jsonify({"success": False, "error": "Plan ID is required"}), 400

        # Get current subscription
        current_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not current_subscription:
            return jsonify({"success": False, "error": "No active subscription to upgrade"}), 404

        # Get new plan
        new_plan = SubscriptionPlan.query.get(new_plan_id)
        if not new_plan or not new_plan.is_active:
            return jsonify({"success": False, "error": "Invalid or inactive plan"}), 404

        # Check if it's actually an upgrade
        if new_plan.price <= current_subscription.plan.price:
            return jsonify({"success": False, "error": "Can only upgrade to higher-tier plans"}), 400

        # Calculate prorated amount
        days_remaining = current_subscription.days_remaining
        daily_rate_old = float(current_subscription.plan.price) / 30
        daily_rate_new = float(new_plan.price) / 30
        prorated_amount = (daily_rate_new - daily_rate_old) * days_remaining

        # Create payment for upgrade
        payment = Payment(
            subscription_id=current_subscription.id,
            amount=prorated_amount,
            currency='USD',
            status='pending',
            provider='paymob',
            extra_data={
                'upgrade': True,
                'from_plan': current_subscription.plan_id,
                'to_plan': new_plan_id,
                'prorated': True,
                'days_remaining': days_remaining
            }
        )

        db.session.add(payment)
        db.session.flush()

        # Process upgrade payment
        payment_result = process_payment_integration(payment, data)

        if payment_result['success']:
            # Update subscription
            old_plan_name = current_subscription.plan.name
            current_subscription.plan_id = new_plan_id
            payment.status = 'completed'
            payment.processed_at = datetime.now(timezone.utc)
            payment.provider_transaction_id = payment_result.get('transaction_id')

            # Update usage limits
            usage_records = current_subscription.usage_records.all()
            for usage in usage_records:
                if usage.feature == 'athletes':
                    usage.usage_limit = new_plan.max_athletes
                elif usage.feature == 'workouts':
                    usage.usage_limit = new_plan.max_workouts
                elif usage.feature == 'storage':
                    usage.usage_limit = new_plan.storage_gb
                usage.updated_at = datetime.now(timezone.utc)

            db.session.commit()

            return jsonify({
                "success": True,
                "message": f"Successfully upgraded from {old_plan_name} to {new_plan.name}!",
                "new_plan": new_plan.name,
                "prorated_amount": float(prorated_amount),
                "payment_url": payment_result.get('payment_url')
            })
        else:
            payment.status = 'failed'
            payment.failure_reason = payment_result.get('error')
            db.session.commit()

            return jsonify({
                "success": False,
                "error": f"Upgrade payment failed: {payment_result.get('error')}"
            }), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error upgrading plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/payment_history', methods=['GET'])
@jwt_required()
def get_payment_history():
    """Get user's payment history"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
        status = request.args.get('status', '')

        # Get all user's subscriptions
        user_subscriptions = Subscription.query.filter_by(user_id=identity).all()
        subscription_ids = [sub.id for sub in user_subscriptions]

        # Build payment query
        payments_query = Payment.query.filter(
            Payment.subscription_id.in_(subscription_ids)
        )

        if status:
            payments_query = payments_query.filter(Payment.status == status)

        # Get paginated payments
        payments = payments_query.order_by(Payment.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        payment_data = []
        for payment in payments.items:
            payment_data.append({
                'id': payment.id,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'provider': payment.provider,
                'provider_transaction_id': payment.provider_transaction_id,
                'date': payment.processed_at.strftime('%b %d, %Y') if payment.processed_at else payment.created_at.strftime('%b %d, %Y'),
                'plan_name': payment.subscription.plan.name if payment.subscription and payment.subscription.plan else 'N/A',
                'subscription_id': payment.subscription_id,
                'is_upgrade': payment.extra_data and payment.extra_data.get('upgrade', False),
                'failure_reason': payment.failure_reason,
                'billing_cycle': payment.extra_data.get('billing_cycle', 'monthly') if payment.extra_data else 'monthly'
            })

        return jsonify({
            "success": True,
            "payments": payment_data,
            "pagination": {
                "page": payments.page,
                "pages": payments.pages,
                "per_page": payments.per_page,
                "total": payments.total
            }
        })

    except Exception as e:
        logging.error(f"Error getting payment history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/subscription_usage', methods=['GET'])
@jwt_required()
def get_subscription_usage():
    """Get detailed usage information"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Get current subscription
        subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not subscription:
            return jsonify({"success": False, "error": "No active subscription found"}), 404

        # Get usage records
        usage_records = subscription.usage_records.all()
        
        usage_data = []
        for usage in usage_records:
            usage_data.append({
                'feature': usage.feature,
                'feature_name': {
                    'athletes': 'Athletes',
                    'workouts': 'Workouts',
                    'storage': 'Storage (GB)'
                }.get(usage.feature, usage.feature.title()),
                'used': usage.usage_count,
                'limit': usage.usage_limit,
                'percentage': usage.usage_percentage,
                'is_over_limit': usage.is_over_limit,
                'period_start': usage.period_start.strftime('%Y-%m-%d') if usage.period_start else None,
                'period_end': usage.period_end.strftime('%Y-%m-%d') if usage.period_end else None
            })

        return jsonify({
            "success": True,
            "usage_data": usage_data,
            "subscription": {
                'id': subscription.id,
                'plan_name': subscription.plan.name if subscription.plan else None,
                'status': subscription.status,
                'days_remaining': subscription.days_remaining,
                'end_date': subscription.end_date.strftime('%b %d, %Y') if subscription.end_date else None
            }
        })

    except Exception as e:
        logging.error(f"Error getting subscription usage: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/webhook/payment_callback', methods=['POST'])
def payment_callback():
    """Handle payment gateway webhook callbacks"""
    try:
        # Get callback data
        callback_data = request.get_json() or request.form.to_dict()
        
        # Verify webhook signature (implement based on your payment provider)
        if not verify_webhook_signature(callback_data):
            return jsonify({"error": "Invalid signature"}), 403
        
        # Extract callback information
        transaction_id = callback_data.get('id') or callback_data.get('transaction_id')
        order_id = callback_data.get('order', {}).get('id') if isinstance(callback_data.get('order'), dict) else callback_data.get('order_id')
        success = callback_data.get('success') == 'true' or callback_data.get('success') is True
        amount_cents = callback_data.get('amount_cents', 0)
        
        if not transaction_id:
            return jsonify({"error": "Missing transaction ID"}), 400
        
        # Find payment record
        payment = Payment.query.filter(
            or_(
                Payment.provider_transaction_id == str(transaction_id),
                Payment.extra_data.contains({'order_id': order_id}) if order_id else False
            )
        ).first()
        
        if not payment:
            logging.error(f"Payment not found for transaction {transaction_id}")
            return jsonify({"error": "Payment not found"}), 404
        
        # Update payment status
        if success and amount_cents == int(float(payment.amount) * 100):
            payment.status = 'completed'
            payment.processed_at = datetime.now(timezone.utc)
            payment.provider_transaction_id = str(transaction_id)
            
            # Update subscription status
            subscription = payment.subscription
            subscription.status = 'active'
            
            # Create usage records if not exists
            if not subscription.usage_records.first():
                create_usage_records(subscription)
        else:
            payment.status = 'failed'
            payment.failure_reason = callback_data.get('failure_reason', 'Payment verification failed')
            
            # Update subscription status
            subscription = payment.subscription
            subscription.status = 'canceled'
        
        db.session.commit()
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"Error processing payment callback: {e}")
        return jsonify({"error": "Internal server error"}), 500

def verify_webhook_signature(callback_data):
    """Verify webhook signature for security"""
    try:
        # Implement signature verification based on your payment provider
        # This is a simplified example - implement according to your provider's documentation
        
        # For Paymob example:
        # hmac_secret = "your_webhook_secret"
        # signature = callback_data.get('signature')
        # payload = json.dumps(callback_data, sort_keys=True)
        # expected_signature = hmac.new(hmac_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        # return hmac.compare_digest(signature, expected_signature)
        
        # For demo purposes, always return True
        # In production, implement proper signature verification
        return True
        
    except Exception as e:
        logging.error(f"Error verifying webhook signature: {e}")
        return False

@athlete_bp.route('/api/payment_methods', methods=['GET'])
@jwt_required()
def get_payment_methods():
    """Get user's saved payment methods"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        payment_methods = PaymentMethod.query.filter_by(
            user_id=identity,
            is_active=True
        ).order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc()).all()
        
        methods_data = []
        for method in payment_methods:
            methods_data.append({
                'id': method.id,
                'type': method.method_type,
                'display_name': method.display_name(),
                'last_four': method.last_four,
                'brand': method.brand,
                'expires_at': method.expires_at.strftime('%m/%y') if method.expires_at else None,
                'is_default': method.is_default,
                'created_at': method.created_at.strftime('%b %d, %Y')
            })
        
        return jsonify({
            "success": True,
            "payment_methods": methods_data
        })
        
    except Exception as e:
        logging.error(f"Error getting payment methods: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/payment_methods', methods=['POST'])
@jwt_required()
def add_payment_method():
    """Add new payment method"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        method_type = data.get('method_type')
        card_number = data.get('card_number', '').replace(' ', '')
        card_expiry = data.get('card_expiry', '')
        is_default = data.get('is_default', False)

        if method_type == 'card':
            if not card_number or len(card_number) < 16:
                return jsonify({"success": False, "error": "Invalid card number"}), 400
            
            if not card_expiry:
                return jsonify({"success": False, "error": "Card expiry is required"}), 400

            # Extract card details
            last_four = card_number[-4:]
            brand = detect_card_brand(card_number)
            
            # Parse expiry date
            try:
                month, year = card_expiry.split('/')
                expires_at = datetime(int(f"20{year}"), int(month), 1).date()
            except:
                return jsonify({"success": False, "error": "Invalid expiry format. Use MM/YY"}), 400

            # If setting as default, update other methods
            if is_default:
                PaymentMethod.query.filter_by(
                    user_id=identity,
                    is_default=True
                ).update({'is_default': False})

            # Create payment method
            payment_method = PaymentMethod(
                user_id=identity,
                method_type=method_type,
                provider='paymob',
                last_four=last_four,
                brand=brand,
                expires_at=expires_at,
                is_default=is_default,
                is_active=True
            )

            db.session.add(payment_method)
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Payment method added successfully",
                "payment_method": {
                    'id': payment_method.id,
                    'display_name': payment_method.display_name(),
                    'is_default': payment_method.is_default
                }
            })
        
        else:
            return jsonify({"success": False, "error": "Unsupported payment method type"}), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding payment method: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

def detect_card_brand(card_number):
    """Detect card brand from card number"""
    if card_number.startswith('4'):
        return 'visa'
    elif card_number.startswith('5') or card_number.startswith('2'):
        return 'mastercard'
    elif card_number.startswith('3'):
        return 'amex'
    else:
        return 'unknown'

@athlete_bp.route('/api/subscription_history', methods=['GET'])
@jwt_required()
def get_subscription_history():
    """Get user's subscription history"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Get paginated subscription history
        subscriptions = Subscription.query.filter_by(
            user_id=identity
        ).order_by(Subscription.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        subscription_data = []
        for sub in subscriptions.items:
            subscription_data.append({
                'id': sub.id,
                'plan_name': sub.plan.name if sub.plan else 'Unknown Plan',
                'price': float(sub.plan.price) if sub.plan else 0.0,
                'status': sub.status,
                'start_date': sub.start_date.strftime('%b %d, %Y') if sub.start_date else None,
                'end_date': sub.end_date.strftime('%b %d, %Y') if sub.end_date else None,
                'billing_cycle': sub.billing_cycle,
                'auto_renew': sub.auto_renew,
                'total_paid': sub.total_paid,
                'days_remaining': sub.days_remaining if sub.status in ['active', 'trial'] else 0,
                'cancelled_at': sub.canceled_at.strftime('%b %d, %Y') if sub.canceled_at else None,
                'cancellation_reason': sub.cancellation_reason
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
        logging.error(f"Error getting subscription history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/convert_trial', methods=['POST'])
@jwt_required()
def convert_trial():
    """Convert trial subscription to paid"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        
        # Get current trial subscription
        trial_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status == 'trial'
        ).first()

        if not trial_subscription:
            return jsonify({"success": False, "error": "No trial subscription found"}), 404

        # Create payment for trial conversion
        plan_price = float(trial_subscription.plan.price)
        
        payment = Payment(
            subscription_id=trial_subscription.id,
            amount=plan_price,
            currency='USD',
            status='pending',
            provider='paymob',
            extra_data={
                'trial_conversion': True,
                'original_trial_end': trial_subscription.trial_end_date.isoformat() if trial_subscription.trial_end_date else None
            }
        )

        db.session.add(payment)
        db.session.flush()

        # Process payment
        payment_result = process_payment_integration(payment, data)

        if payment_result['success']:
            # Convert trial to active subscription
            trial_subscription.status = 'active'
            trial_subscription.trial_end_date = None
            payment.status = 'completed'
            payment.processed_at = datetime.now(timezone.utc)
            payment.provider_transaction_id = payment_result.get('transaction_id')

            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Trial successfully converted to paid subscription!",
                "payment_url": payment_result.get('payment_url')
            })
        else:
            payment.status = 'failed'
            payment.failure_reason = payment_result.get('error')
            db.session.commit()

            return jsonify({
                "success": False,
                "error": f"Trial conversion failed: {payment_result.get('error')}"
            }), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error converting trial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@athlete_bp.route('/api/update_auto_renew', methods=['POST'])
@jwt_required()
def update_auto_renew():
    """Update auto-renewal setting for current subscription"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        auto_renew = data.get('auto_renew')
        if auto_renew is None:
            return jsonify({"success": False, "error": "auto_renew parameter is required"}), 400

        # Get current subscription
        subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not subscription:
            return jsonify({"success": False, "error": "No active subscription found"}), 404

        # Update auto-renewal setting
        subscription.auto_renew = bool(auto_renew)
        
        if auto_renew:
            subscription.next_billing_date = subscription.end_date
        else:
            subscription.next_billing_date = None
        
        subscription.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Auto-renewal {'enabled' if auto_renew else 'disabled'} successfully",
            "auto_renew": subscription.auto_renew
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating auto-renew: {e}")
        return jsonify({"success": False, "error": str(e)}), 500