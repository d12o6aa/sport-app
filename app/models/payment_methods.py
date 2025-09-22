from datetime import datetime, timedelta
from app.extensions import db
from enum import Enum

class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    method_type = db.Column(db.String(50), nullable=False)  # paypal, stripe, bank_transfer
    provider_id = db.Column(db.String(255))  # External provider ID
    last_four = db.Column(db.String(4))  # Last 4 digits for cards
    brand = db.Column(db.String(50))  # visa, mastercard, etc.
    expires_at = db.Column(db.Date)  # For cards
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User", backref="payment_methods")
    payments = db.relationship("Payment", back_populates="payment_method", lazy="dynamic")
