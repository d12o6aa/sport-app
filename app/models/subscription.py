from datetime import datetime
from app.extensions import db

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plan_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('active','expired','canceled')"),
        default="active",
        index=True,
    )
    image_url = db.Column(db.String(255), nullable=True)

    user = db.relationship("User", back_populates="subscriptions")

    __table_args__ = (
        db.Index("idx_subscription_user_id", "user_id"),
    )
