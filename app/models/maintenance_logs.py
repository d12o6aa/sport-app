from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
class MaintenanceLog(db.Model):
    __tablename__ = "maintenance_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey("equipments.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    maintenance_type = db.Column(
        db.String(30),
        db.CheckConstraint("maintenance_type IN ('routine','repair','inspection','replacement')"),
        nullable=False
    )
    
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Float)
    parts_replaced = db.Column(JSONB, default=list)
    
    scheduled_date = db.Column(db.Date)
    completed_date = db.Column(db.Date)
    next_maintenance_date = db.Column(db.Date)
    
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('scheduled','in_progress','completed','cancelled')"),
        default='scheduled'
    )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment = db.relationship("Equipment", back_populates="maintenance_logs")
    technician = db.relationship("User", back_populates="maintenance_logs")  # Added back_populates