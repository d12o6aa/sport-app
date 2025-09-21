from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class EventRegistration(db.Model):
    __tablename__ = "event_registrations"
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_status = db.Column(
        db.String(20),
        db.CheckConstraint("payment_status IN ('pending','paid','refunded','failed')"),
        default='pending'
    )
    attendance_status = db.Column(
        db.String(20),
        db.CheckConstraint("attendance_status IN ('registered','attended','no_show','cancelled')"),
        default='registered'
    )
    
    notes = db.Column(db.Text)
    
    # Relationships
    event = db.relationship("Event", back_populates="registrations")
    user = db.relationship("User", back_populates="event_registrations")  # Added back_populates
