from datetime import datetime, timedelta
from app.extensions import db
from enum import Enum

class Payment(db.Model):
    __tablename__ = "payments"
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id"))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('pending','completed','failed','refunded','canceled')"),
        default="pending"
    )
    provider = db.Column(db.String(50))  # paypal, stripe, bank
    provider_transaction_id = db.Column(db.String(255))
    provider_fee = db.Column(db.Numeric(10, 2))
    failure_reason = db.Column(db.Text)
    extra_data = db.Column(db.JSON)  # Store provider-specific data
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship("Subscription", back_populates="payments")
    payment_method = db.relationship("PaymentMethod", back_populates="payments")
