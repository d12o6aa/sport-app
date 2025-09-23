from datetime import datetime, timedelta, timezone
from app.extensions import db


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=False)
    
    # Subscription details
    start_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime)
    trial_end_date = db.Column(db.DateTime)
    auto_renew = db.Column(db.Boolean, default=True)
    
    # Status and lifecycle
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('trial','active','past_due','canceled','expired','suspended')"),
        default="trial",
        index=True,
    )
    
    # Billing
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly
    next_billing_date = db.Column(db.DateTime)
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    
    # Cancellation
    canceled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.String(255))
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    
    # Usage tracking
    usage_data = db.Column(db.JSON)  # Track feature usage
    last_activity_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="subscriptions")
    plan = db.relationship("SubscriptionPlan", back_populates="subscriptions")
    payments = db.relationship("Payment", back_populates="subscription", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("idx_subscription_user_id", "user_id"),
        db.Index("idx_subscription_status", "status"),
        db.Index("idx_subscription_end_date", "end_date"),
    )
    
    @property
    def is_active(self):
        return self.status == 'active' and self.end_date and self.end_date > datetime.now(timezone.utc)
    
    @property
    def is_trial(self):
        return self.status == 'trial' and self.trial_end_date and self.trial_end_date > datetime.now(timezone.utc)
    
    @property
    def days_remaining(self):
        if self.end_date:
            delta = self.end_date - datetime.now(timezone.utc)
            return max(0, delta.days)
        return 0
    
    @property
    def total_paid(self):
        return sum(p.amount for p in self.payments if p.status == 'completed')
    
    def extend_subscription(self, months=None):
        """Extend subscription by plan duration or specified months"""
        if not months:
            months = self.plan.duration_months
        
        now = datetime.now(timezone.utc)
        if self.end_date and self.end_date > now:
            # Extend from current end date
            self.end_date = self.end_date + timedelta(days=30 * months)
        else:
            # Start from now
            self.end_date = now + timedelta(days=30 * months)
        
        self.status = 'active'
        self.updated_at = now
        if self.auto_renew:
            self.next_billing_date = self.end_date
        self.current_period_end = self.end_date
    
    def cancel_subscription(self, reason=None, immediate=False):
        """Cancel subscription"""
        now = datetime.now(timezone.utc)
        self.cancellation_reason = reason
        self.canceled_at = now
        
        if immediate:
            self.status = 'canceled'
            self.end_date = now
            self.current_period_end = now
            self.next_billing_date = None
        else:
            self.cancel_at_period_end = True
        
        self.auto_renew = False
        self.updated_at = now