from datetime import datetime, timedelta
from app.extensions import db
from enum import Enum

class SubscriptionUsage(db.Model):
    __tablename__ = "subscription_usage"
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscriptions.id"), nullable=False)
    feature = db.Column(db.String(100), nullable=False)  # workouts, storage, athletes
    usage_count = db.Column(db.Integer, default=0)
    usage_limit = db.Column(db.Integer)
    period_start = db.Column(db.DateTime, default=datetime.utcnow)
    period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = db.relationship("Subscription", backref="usage_records")
    
    @property
    def usage_percentage(self):
        if self.usage_limit and self.usage_limit > 0:
            return min(100, (self.usage_count / self.usage_limit) * 100)
        return 0
    
    @property
    def is_over_limit(self):
        return self.usage_limit and self.usage_count > self.usage_limit