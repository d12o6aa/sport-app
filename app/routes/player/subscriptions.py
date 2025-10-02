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
import json
import os

from . import athlete_bp

# ============= Configuration =============
PAYMOB_API_KEY = os.getenv('PAYMOB_API_KEY', 'your_paymob_api_key')
PAYMOB_INTEGRATION_ID_CARD = os.getenv('PAYMOB_INTEGRATION_ID_CARD', 'your_card_integration_id')
PAYMOB_IFRAME_ID = os.getenv('PAYMOB_IFRAME_ID', 'your_iframe_id')
PAYMOB_HMAC_SECRET = os.getenv('PAYMOB_HMAC_SECRET', 'your_hmac_secret')

PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', 'your_paypal_client_id')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET', 'your_paypal_secret')
PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')  # sandbox or live
PAYPAL_API_BASE = 'https://api-m.sandbox.paypal.com' if PAYPAL_MODE == 'sandbox' else 'https://api-m.paypal.com'

APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5000')


def is_athlete_or_coach(identity):
    """Check if the user is athlete or coach"""
    user = User.query.filter_by(id=identity).first()
    return user and user.role in ['athlete', 'coach']


def get_subscription_metrics(user_id):
    """Generate subscription metrics for athlete/coach"""
    try:
        now = datetime.now(tz=timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        
        current_subscription = Subscription.query.filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        total_subscriptions = Subscription.query.filter_by(user_id=user_id).count()
        
        total_spent = db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).join(Subscription).filter(
            Subscription.user_id == user_id,
            Payment.status == 'completed'
        ).scalar() or 0
        
        days_remaining = 0
        if current_subscription and current_subscription.end_date:
            delta = current_subscription.end_date - now
            days_remaining = max(0, delta.days)
        
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


# ============= PAYMOB Integration =============
class PaymobGateway:
    """Paymob Payment Gateway Integration"""
    
    @staticmethod
    def get_auth_token():
        """Get authentication token from Paymob"""
        try:
            response = requests.post(
                "https://accept.paymob.com/api/auth/tokens",
                json={"api_key": PAYMOB_API_KEY},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("token")
        except Exception as e:
            logging.error(f"Paymob auth error: {e}")
            return None
    
    @staticmethod
    def create_order(auth_token, amount, currency, items):
        """Create payment order"""
        try:
            response = requests.post(
                "https://accept.paymob.com/api/ecommerce/orders",
                json={
                    "auth_token": auth_token,
                    "delivery_needed": "false",
                    "amount_cents": int(float(amount) * 100),
                    "currency": currency,
                    "items": items
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Paymob order creation error: {e}")
            return None
    
    @staticmethod
    def get_payment_key(auth_token, amount, currency, order_id, billing_data, integration_id):
        """Generate payment key for iframe"""
        try:
            response = requests.post(
                "https://accept.paymob.com/api/acceptance/payment_keys",
                json={
                    "auth_token": auth_token,
                    "amount_cents": int(float(amount) * 100),
                    "expiration": 3600,
                    "order_id": order_id,
                    "billing_data": billing_data,
                    "currency": currency,
                    "integration_id": integration_id,
                    "lock_order_when_paid": "false"
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("token")
        except Exception as e:
            logging.error(f"Paymob payment key error: {e}")
            return None
    
    @staticmethod
    def initiate_payment(payment, user):
        """Complete Paymob payment flow"""
        try:
            # Step 1: Get auth token
            auth_token = PaymobGateway.get_auth_token()
            if not auth_token:
                return {"success": False, "error": "Failed to authenticate with payment gateway"}
            
            # Step 2: Create order
            order_data = PaymobGateway.create_order(
                auth_token=auth_token,
                amount=payment.amount,
                currency=payment.currency,
                items=[{
                    "name": f"Subscription - {payment.subscription.plan.name}",
                    "amount_cents": int(float(payment.amount) * 100),
                    "description": f"Subscription for {user.email}",
                    "quantity": "1"
                }]
            )
            
            if not order_data:
                return {"success": False, "error": "Failed to create payment order"}
            
            order_id = order_data.get("id")
            
            # Step 3: Generate payment key
            billing_data = {
                "apartment": "NA",
                "email": user.email,
                "floor": "NA",
                "first_name": user.name.split()[0] if user.name else "User",
                "street": "NA",
                "building": "NA",
                "phone_number": getattr(user.athlete_profile, 'phone', '+201000000000') if user.athlete_profile else "+201000000000",
                "shipping_method": "NA",
                "postal_code": "NA",
                "city": "Cairo",
                "country": "EG",
                "last_name": user.name.split()[-1] if len(user.name.split()) > 1 else "User",
                "state": "Cairo"
            }
            
            payment_key = PaymobGateway.get_payment_key(
                auth_token=auth_token,
                amount=payment.amount,
                currency=payment.currency,
                order_id=order_id,
                billing_data=billing_data,
                integration_id=PAYMOB_INTEGRATION_ID_CARD
            )
            
            if not payment_key:
                return {"success": False, "error": "Failed to generate payment key"}
            
            # Update payment with order details
            payment.provider_transaction_id = f"ord_{order_id}"
            payment.extra_data = payment.extra_data or {}
            payment.extra_data.update({
                'order_id': order_id,
                'payment_key': payment_key
            })
            
            return {
                "success": True,
                "payment_url": f"https://accept.paymob.com/api/acceptance/iframes/{PAYMOB_IFRAME_ID}?payment_token={payment_key}",
                "transaction_id": f"ord_{order_id}",
                "order_id": order_id
            }
            
        except Exception as e:
            logging.error(f"Paymob initiation error: {e}")
            return {"success": False, "error": str(e)}


# ============= PayPal Integration =============
class PayPalGateway:
    """PayPal Payment Gateway Integration"""
    
    @staticmethod
    def get_access_token():
        """Get PayPal access token"""
        try:
            response = requests.post(
                f"{PAYPAL_API_BASE}/v1/oauth2/token",
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
                auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
                data={"grant_type": "client_credentials"},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            logging.error(f"PayPal auth error: {e}")
            return None
    
    @staticmethod
    def create_order(access_token, payment, user):
        """Create PayPal order"""
        try:
            response = requests.post(
                f"{PAYPAL_API_BASE}/v2/checkout/orders",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "reference_id": f"payment_{payment.id}",
                        "description": f"Subscription - {payment.subscription.plan.name}",
                        "amount": {
                            "currency_code": payment.currency,
                            "value": str(float(payment.amount))
                        }
                    }],
                    "application_context": {
                        "return_url": f"{APP_BASE_URL}/athlete/payment/paypal/success",
                        "cancel_url": f"{APP_BASE_URL}/athlete/payment/paypal/cancel",
                        "brand_name": "Sports Management System",
                        "user_action": "PAY_NOW"
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"PayPal order creation error: {e}")
            return None
    
    @staticmethod
    def initiate_payment(payment, user):
        """Complete PayPal payment flow"""
        try:
            # Get access token
            access_token = PayPalGateway.get_access_token()
            if not access_token:
                return {"success": False, "error": "Failed to authenticate with PayPal"}
            
            # Create order
            order_data = PayPalGateway.create_order(access_token, payment, user)
            if not order_data:
                return {"success": False, "error": "Failed to create PayPal order"}
            
            order_id = order_data.get("id")
            approve_link = next((link["href"] for link in order_data.get("links", []) if link["rel"] == "approve"), None)
            
            if not approve_link:
                return {"success": False, "error": "Failed to get PayPal approval link"}
            
            # Update payment with order details
            payment.provider_transaction_id = order_id
            payment.extra_data = payment.extra_data or {}
            payment.extra_data.update({
                'paypal_order_id': order_id,
                'paypal_order_status': order_data.get('status')
            })
            
            return {
                "success": True,
                "payment_url": approve_link,
                "transaction_id": order_id
            }
            
        except Exception as e:
            logging.error(f"PayPal initiation error: {e}")
            return {"success": False, "error": str(e)}


# ============= Main Routes =============
@athlete_bp.route('/subscriptions', methods=['GET'])
@jwt_required()
def subscriptions():
    """Render subscription management page"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        user = User.query.get(identity)
        metrics = get_subscription_metrics(identity)
        
        available_plans = SubscriptionPlan.query.filter_by(
            is_active=True
        ).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.price).all()
        
        subscription_history = Subscription.query.filter_by(
            user_id=identity
        ).order_by(Subscription.created_at.desc()).limit(10).all()
        
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


@athlete_bp.route('/api/subscribe', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create subscription and redirect to payment gateway"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        plan_id = data.get('plan_id')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payment_method = data.get('payment_method', 'card')  # 'card' or 'paypal'
        auto_renew = data.get('auto_renew', True)
        trial_enabled = data.get('trial_enabled', False)

        if not plan_id:
            return jsonify({"success": False, "error": "Plan ID is required"}), 400

        user = User.query.get(identity)
        
        # Check existing subscription
        existing_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()
        
        if existing_subscription:
            return jsonify({
                "success": False,
                "error": "You already have an active subscription"
            }), 400

        # Get plan
        plan = SubscriptionPlan.query.get(plan_id)
        if not plan or not plan.is_active:
            return jsonify({"success": False, "error": "Invalid plan"}), 404

        # Calculate pricing
        base_price = float(plan.price)
        final_price = base_price
        duration_days = 30 * plan.duration_months
        
        if billing_cycle == 'yearly':
            final_price = base_price * 12 * 0.8
            duration_days = 365
        elif billing_cycle == 'quarterly':
            final_price = base_price * 3 * 0.9
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
            current_period_end=end_date
        )

        db.session.add(subscription)
        db.session.flush()

        # Handle trial or payment
        if trial_enabled:
            subscription.status = 'trial'
            create_usage_records(subscription)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Trial subscription created successfully!",
                "subscription_id": subscription.id,
                "trial_days": 14,
                "redirect_url": url_for('athlete.subscriptions')
            })
        
        # Create payment record
        payment = Payment(
            subscription_id=subscription.id,
            amount=final_price,
            currency='USD',
            status='pending',
            provider='paymob' if payment_method == 'card' else 'paypal',
            extra_data={
                'billing_cycle': billing_cycle,
                'payment_method': payment_method
            }
        )

        db.session.add(payment)
        db.session.flush()

        # Initiate payment gateway
        if payment_method == 'card':
            payment_result = PaymobGateway.initiate_payment(payment, user)
        elif payment_method == 'paypal':
            payment_result = PayPalGateway.initiate_payment(payment, user)
        else:
            return jsonify({"success": False, "error": "Invalid payment method"}), 400

        if payment_result['success']:
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Redirecting to payment gateway...",
                "payment_url": payment_result['payment_url'],
                "subscription_id": subscription.id
            })
        else:
            subscription.status = 'canceled'
            payment.status = 'failed'
            payment.failure_reason = payment_result.get('error')
            db.session.commit()
            
            return jsonify({
                "success": False,
                "error": payment_result.get('error')
            }), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating subscription: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def create_usage_records(subscription):
    """Create usage tracking records"""
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


# ============= Webhook Handlers =============
@athlete_bp.route('/webhook/paymob', methods=['POST'])
def paymob_webhook():
    """Handle Paymob payment callbacks"""
    try:
        data = request.json
        
        # Verify HMAC
        received_hmac = request.args.get('hmac')
        if received_hmac and not verify_paymob_hmac(data, received_hmac):
            logging.error("Invalid Paymob HMAC signature")
            return jsonify({"error": "Invalid signature"}), 403
        
        # Extract data
        transaction_id = data.get('id')
        order_id = data.get('order', {}).get('id') if isinstance(data.get('order'), dict) else data.get('order')
        success = data.get('success') == 'true' or data.get('success') is True
        amount_cents = int(data.get('amount_cents', 0))
        
        # Find payment
        payment = Payment.query.filter(
            Payment.extra_data.contains({'order_id': order_id})
        ).first()
        
        if not payment:
            logging.error(f"Payment not found for order {order_id}")
            return jsonify({"error": "Payment not found"}), 404
        
        # Verify amount
        expected_amount_cents = int(float(payment.amount) * 100)
        
        if success and amount_cents == expected_amount_cents:
            # Payment successful
            payment.status = 'completed'
            payment.processed_at = datetime.now(timezone.utc)
            payment.provider_transaction_id = str(transaction_id)
            
            subscription = payment.subscription
            subscription.status = 'active'
            
            if not subscription.usage_records.first():
                create_usage_records(subscription)
            
            db.session.commit()
            
            logging.info(f"Payment {payment.id} completed successfully")
        else:
            # Payment failed
            payment.status = 'failed'
            payment.failure_reason = data.get('data', {}).get('message', 'Payment verification failed')
            
            subscription = payment.subscription
            subscription.status = 'canceled'
            
            db.session.commit()
            
            logging.warning(f"Payment {payment.id} failed")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"Paymob webhook error: {e}")
        return jsonify({"error": "Internal error"}), 500


@athlete_bp.route('/webhook/paypal', methods=['POST'])
def paypal_webhook():
    """Handle PayPal payment webhooks"""
    try:
        data = request.json
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        
        order_id = resource.get('id')
        
        # Find payment
        payment = Payment.query.filter(
            Payment.provider_transaction_id == order_id
        ).first()
        
        if not payment:
            logging.error(f"Payment not found for PayPal order {order_id}")
            return jsonify({"error": "Payment not found"}), 404
        
        # Handle different event types
        if event_type == 'CHECKOUT.ORDER.APPROVED':
            # Order approved - now capture it
            access_token = PayPalGateway.get_access_token()
            if access_token:
                capture_response = requests.post(
                    f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}"
                    },
                    timeout=30
                )
                
                if capture_response.ok:
                    capture_data = capture_response.json()
                    if capture_data.get('status') == 'COMPLETED':
                        payment.status = 'completed'
                        payment.processed_at = datetime.now(timezone.utc)
                        
                        subscription = payment.subscription
                        subscription.status = 'active'
                        
                        if not subscription.usage_records.first():
                            create_usage_records(subscription)
                        
                        db.session.commit()
                        
                        logging.info(f"PayPal payment {payment.id} completed")
        
        elif event_type == 'PAYMENT.CAPTURE.COMPLETED':
            payment.status = 'completed'
            payment.processed_at = datetime.now(timezone.utc)
            
            subscription = payment.subscription
            subscription.status = 'active'
            
            db.session.commit()
        
        elif event_type in ['PAYMENT.CAPTURE.DENIED', 'CHECKOUT.ORDER.VOIDED']:
            payment.status = 'failed'
            payment.failure_reason = 'Payment denied or voided'
            
            subscription = payment.subscription
            subscription.status = 'canceled'
            
            db.session.commit()
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"PayPal webhook error: {e}")
        return jsonify({"error": "Internal error"}), 500


# ============= Payment Success/Cancel Handlers =============
@athlete_bp.route('/payment/paypal/success', methods=['GET'])
@jwt_required()
def paypal_success():
    """Handle PayPal return after successful payment"""
    try:
        token = request.args.get('token')
        
        # The actual payment capture is handled by webhook
        # Just redirect user to subscriptions page
        
        return redirect(url_for('athlete.subscriptions'))
        
    except Exception as e:
        logging.error(f"PayPal success handler error: {e}")
        return redirect(url_for('athlete.subscriptions'))


@athlete_bp.route('/payment/paypal/cancel', methods=['GET'])
@jwt_required()
def paypal_cancel():
    """Handle PayPal cancellation"""
    try:
        token = request.args.get('token')
        
        # Find and cancel the payment
        payment = Payment.query.filter(
            Payment.extra_data.contains({'paypal_order_id': token}),
            Payment.status == 'pending'
        ).first()
        
        if payment:
            payment.status = 'canceled'
            payment.subscription.status = 'canceled'
            db.session.commit()
        
        return redirect(url_for('athlete.subscriptions'))
        
    except Exception as e:
        logging.error(f"PayPal cancel handler error: {e}")
        return redirect(url_for('athlete.subscriptions'))


def verify_paymob_hmac(data, received_hmac):
    """Verify Paymob HMAC signature"""
    try:
        # Construct string to hash (based on Paymob documentation)
        concatenated_string = (
            f"{data.get('amount_cents')}"
            f"{data.get('created_at')}"
            f"{data.get('currency')}"
            f"{data.get('error_occured')}"
            f"{data.get('has_parent_transaction')}"
            f"{data.get('id')}"
            f"{data.get('integration_id')}"
            f"{data.get('is_3d_secure')}"
            f"{data.get('is_auth')}"
            f"{data.get('is_capture')}"
            f"{data.get('is_refunded')}"
            f"{data.get('is_standalone_payment')}"
            f"{data.get('is_voided')}"
            f"{data.get('order')}"
            f"{data.get('owner')}"
            f"{data.get('pending')}"
            f"{data.get('source_data', {}).get('pan')}"
            f"{data.get('source_data', {}).get('sub_type')}"
            f"{data.get('source_data', {}).get('type')}"
            f"{data.get('success')}"
        )
        
        calculated_hmac = hmac.new(
            PAYMOB_HMAC_SECRET.encode(),
            concatenated_string.encode(),
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hmac, received_hmac)
        
    except Exception as e:
        logging.error(f"HMAC verification error: {e}")
        return False


# ============= Additional API Endpoints =============
@athlete_bp.route('/api/payment_status/<int:payment_id>', methods=['GET'])
@jwt_required()
def check_payment_status(payment_id):
    """Check payment status"""
    identity = get_jwt_identity()
    
    try:
        payment = Payment.query.join(Subscription).filter(
            Payment.id == payment_id,
            Subscription.user_id == identity
        ).first()
        
        if not payment:
            return jsonify({"success": False, "error": "Payment not found"}), 404
        
        return jsonify({
            "success": True,
            "payment": {
                "id": payment.id,
                "status": payment.status,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "provider": payment.provider,
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                "subscription_id": payment.subscription_id,
                "subscription_status": payment.subscription.status if payment.subscription else None
            }
        })
        
    except Exception as e:
        logging.error(f"Error checking payment status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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
        cancel_type = data.get('cancel_type', 'end_of_period')
        immediate = cancel_type == 'immediate'

        subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not subscription:
            return jsonify({"success": False, "error": "No active subscription found"}), 404

        subscription.cancel_subscription(reason=reason, immediate=immediate)
        db.session.commit()

        message = "Subscription cancelled immediately" if immediate else "Subscription will be cancelled at the end of current period"

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error cancelling subscription: {e}")
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

        user_subscriptions = Subscription.query.filter_by(user_id=identity).all()
        subscription_ids = [sub.id for sub in user_subscriptions]

        payments = Payment.query.filter(
            Payment.subscription_id.in_(subscription_ids)
        ).order_by(Payment.created_at.desc()).paginate(
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
                'plan_name': payment.subscription.plan.name if payment.subscription and payment.subscription.plan else 'N/A'
            })

        return jsonify({
            "success": True,
            "payments": payment_data,
            "pagination": {
                "page": payments.page,
                "pages": payments.pages,
                "total": payments.total
            }
        })

    except Exception as e:
        logging.error(f"Error getting payment history: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@athlete_bp.route('/api/upgrade_plan', methods=['POST'])
@jwt_required()
def upgrade_plan():
    """Upgrade subscription to higher plan"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        new_plan_id = data.get('plan_id')
        payment_method = data.get('payment_method', 'card')

        if not new_plan_id:
            return jsonify({"success": False, "error": "Plan ID required"}), 400

        user = User.query.get(identity)
        current_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not current_subscription:
            return jsonify({"success": False, "error": "No active subscription"}), 404

        new_plan = SubscriptionPlan.query.get(new_plan_id)
        if not new_plan or not new_plan.is_active:
            return jsonify({"success": False, "error": "Invalid plan"}), 404

        if new_plan.price <= current_subscription.plan.price:
            return jsonify({"success": False, "error": "Can only upgrade to higher-tier plans"}), 400

        # Calculate prorated amount
        days_remaining = current_subscription.days_remaining
        daily_rate_old = float(current_subscription.plan.price) / 30
        daily_rate_new = float(new_plan.price) / 30
        prorated_amount = (daily_rate_new - daily_rate_old) * days_remaining

        # Create payment
        payment = Payment(
            subscription_id=current_subscription.id,
            amount=prorated_amount,
            currency='USD',
            status='pending',
            provider='paymob' if payment_method == 'card' else 'paypal',
            extra_data={
                'upgrade': True,
                'from_plan': current_subscription.plan_id,
                'to_plan': new_plan_id,
                'prorated': True
            }
        )

        db.session.add(payment)
        db.session.flush()

        # Initiate payment
        if payment_method == 'card':
            payment_result = PaymobGateway.initiate_payment(payment, user)
        else:
            payment_result = PayPalGateway.initiate_payment(payment, user)

        if payment_result['success']:
            # Update subscription plan (will be activated after payment)
            payment.extra_data['new_plan_id'] = new_plan_id
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Redirecting to payment gateway...",
                "payment_url": payment_result['payment_url'],
                "prorated_amount": float(prorated_amount)
            })
        else:
            payment.status = 'failed'
            db.session.commit()
            return jsonify({"success": False, "error": payment_result.get('error')}), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error upgrading plan: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@athlete_bp.route('/api/convert_trial', methods=['POST'])
@jwt_required()
def convert_trial():
    """Convert trial to paid subscription"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json() or {}
        payment_method = data.get('payment_method', 'card')

        user = User.query.get(identity)
        trial_subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status == 'trial'
        ).first()

        if not trial_subscription:
            return jsonify({"success": False, "error": "No trial subscription"}), 404

        plan_price = float(trial_subscription.plan.price)

        payment = Payment(
            subscription_id=trial_subscription.id,
            amount=plan_price,
            currency='USD',
            status='pending',
            provider='paymob' if payment_method == 'card' else 'paypal',
            extra_data={'trial_conversion': True}
        )

        db.session.add(payment)
        db.session.flush()

        if payment_method == 'card':
            payment_result = PaymobGateway.initiate_payment(payment, user)
        else:
            payment_result = PayPalGateway.initiate_payment(payment, user)

        if payment_result['success']:
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "Redirecting to payment...",
                "payment_url": payment_result['payment_url']
            })
        else:
            payment.status = 'failed'
            db.session.commit()
            return jsonify({"success": False, "error": payment_result.get('error')}), 400

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error converting trial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@athlete_bp.route('/api/update_auto_renew', methods=['POST'])
@jwt_required()
def update_auto_renew():
    """Update auto-renewal setting"""
    identity = get_jwt_identity()
    if not is_athlete_or_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        data = request.get_json()
        auto_renew = data.get('auto_renew')

        subscription = Subscription.query.filter(
            Subscription.user_id == identity,
            Subscription.status.in_(['active', 'trial'])
        ).first()

        if not subscription:
            return jsonify({"success": False, "error": "No active subscription"}), 404

        subscription.auto_renew = bool(auto_renew)
        subscription.next_billing_date = subscription.end_date if auto_renew else None
        subscription.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Auto-renewal {'enabled' if auto_renew else 'disabled'}",
            "auto_renew": subscription.auto_renew
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating auto-renew: {e}")
        return jsonify({"success": False, "error": str(e)}), 500