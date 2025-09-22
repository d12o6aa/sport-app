from datetime import datetime, timedelta
from app.extensions import db
from enum import Enum

class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)  # 1, 3, 6, 12 months
    features = db.Column(db.JSON)  # Store plan features as JSON
    max_athletes = db.Column(db.Integer)  # For coaches
    max_workouts = db.Column(db.Integer)
    storage_gb = db.Column(db.Integer)
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
