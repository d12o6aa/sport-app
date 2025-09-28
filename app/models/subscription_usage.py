
# app/models/subscription_usage.py
from datetime import datetime
from app.extensions import db


class SubscriptionUsage(db.Model):
    __tablename__ = "subscription_usage"
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=False)
    feature = db.Column(db.String(100), nullable=False)  # 'athletes', 'workouts', 'storage'
    usage_count = db.Column(db.Integer, default=0)
    usage_limit = db.Column(db.Integer, default=0)
    period_start = db.Column(db.DateTime, default=datetime.utcnow)
    period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship("Subscription", back_populates="usage_records")
    
    __table_args__ = (
        db.Index('idx_subscription_usage_feature', 'subscription_id', 'feature'),
    )
    
    @property
    def usage_percentage(self):
        if self.usage_limit and self.usage_limit > 0:
            return min(100, round((self.usage_count / self.usage_limit) * 100, 1))
        return 0
    
    @property
    def is_over_limit(self):
        return self.usage_limit and self.usage_count > self.usage_limit
    
    def __repr__(self):
        return f'<SubscriptionUsage {self.feature}: {self.usage_count}/{self.usage_limit}>'
