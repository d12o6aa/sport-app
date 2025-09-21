# ================================
# New Supporting Models
# ================================
from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class EquipmentReservation(db.Model):
    __tablename__ = "equipment_reservations"
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipments.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('active','completed','cancelled')"),
        default='active'
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment = db.relationship("Equipment", back_populates="reservations")
    user = db.relationship("User", back_populates="equipment_reservations")  # Added back_populates
