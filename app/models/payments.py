# app/models/payment.py  
from datetime import datetime
from app.extensions import db


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
        default="pending",
        index=True
    )
    provider = db.Column(db.String(50))  # 'stripe', 'paypal', 'bank'
    provider_transaction_id = db.Column(db.String(255))
    provider_fee = db.Column(db.Numeric(10, 2), default=0)
    failure_reason = db.Column(db.Text)
    extra_data = db.Column(db.JSON)  # Store provider-specific data
    processed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship("Subscription", back_populates="payments")
    payment_method = db.relationship("PaymentMethod", back_populates="payments")
    
    __table_args__ = (
        db.Index('idx_payment_subscription_id', 'subscription_id'),
        db.Index('idx_payment_status', 'status'),
        db.Index('idx_payment_processed_at', 'processed_at'),
    )
    
    def __repr__(self):
        return f'<Payment {self.id}: ${self.amount} - {self.status}>'
    
    @property
    def is_successful(self):
        return self.status == 'completed'
    
    @property
    def net_amount(self):
        return float(self.amount) - float(self.provider_fee or 0)
