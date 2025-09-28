# app/models/subscription_plan.py
from datetime import datetime
from app.extensions import db


class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False, default=1)  # 1, 3, 6, 12 months
    features = db.Column(db.JSON, default=list)  # Store plan features as JSON list
    max_athletes = db.Column(db.Integer, default=0)  # For coaches
    max_workouts = db.Column(db.Integer, default=0)
    storage_gb = db.Column(db.Integer, default=1)
    priority_support = db.Column(db.Boolean, default=False)
    analytics_access = db.Column(db.Boolean, default=False)
    custom_branding = db.Column(db.Boolean, default=False)
    api_access = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship("Subscription", back_populates="plan", lazy="dynamic")
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'
    
    @property
    def active_subscriptions_count(self):
        return self.subscriptions.filter_by(status='active').count()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'duration_months': self.duration_months,
            'features': self.features or [],
            'max_athletes': self.max_athletes,
            'max_workouts': self.max_workouts,
            'storage_gb': self.storage_gb,
            'priority_support': self.priority_support,
            'analytics_access': self.analytics_access,
            'custom_branding': self.custom_branding,
            'api_access': self.api_access,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'active_subscriptions': self.active_subscriptions_count
        }

