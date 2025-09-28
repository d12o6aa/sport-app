# app/models/payment_method.py
from datetime import datetime
from app.extensions import db


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    method_type = db.Column(db.String(50), nullable=False)  # 'card', 'paypal', 'bank_transfer'
    provider = db.Column(db.String(50))  # 'stripe', 'paypal', etc.
    provider_id = db.Column(db.String(255))  # External provider ID
    last_four = db.Column(db.String(4))  # Last 4 digits for cards
    brand = db.Column(db.String(50))  # 'visa', 'mastercard', etc.
    expires_at = db.Column(db.Date)  # For cards
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship("User")
    payments = db.relationship("Payment", back_populates="payment_method", lazy="dynamic")
    
    def __repr__(self):
        return f'<PaymentMethod {self.method_type} *{self.last_four}>'
    
    def display_name(self):
        if self.method_type == 'card' and self.brand and self.last_four:
            return f"{self.brand.title()} **** {self.last_four}"
        elif self.method_type == 'paypal':
            return "PayPal"
        else:
            return self.method_type.replace('_', ' ').title()

