from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

# ================================
# Enhanced Equipment Model
# ================================
class Equipment(db.Model):
    __tablename__ = "equipments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Enhanced equipment fields
    equipment_type = db.Column(db.String(50))  # cardio, strength, functional, etc.
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    serial_number = db.Column(db.String(100), unique=True)
    last_used = db.Column(db.DateTime)
    
    # Status and condition
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('available','maintenance','out_of_order','reserved')"),
        nullable=False, 
        default="available",
        index=True
    )
    condition = db.Column(
        db.String(20),
        db.CheckConstraint("condition IN ('excellent','good','fair','poor')"),
        default='good'
    )
    
    # Maintenance tracking
    purchase_date = db.Column(db.Date)
    last_maintenance = db.Column(db.Date)
    next_maintenance = db.Column(db.Date)
    maintenance_interval_days = db.Column(db.Integer, default=90)  # 3 months default
    maintenance_notes = db.Column(db.Text)
    
    # Usage tracking
    usage_hours = db.Column(db.Integer, default=0)
    max_users = db.Column(db.Integer, default=1)  # How many people can use simultaneously
    current_users = db.Column(db.Integer, default=0)
    
    # Location and specifications
    location = db.Column(db.String(100))  # Floor 1, Zone A, etc.
    specifications = db.Column(JSONB, default=dict)  # Weight limits, dimensions, etc.
    
    # Media
    image_url = db.Column(db.String(255))
    manual_url = db.Column(db.String(255))  # Link to user manual
    
    # New: Owner of the equipment
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Can be nullable if not all equipment has an owner
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reservations = db.relationship("EquipmentReservation", back_populates="equipment", cascade="all, delete-orphan")
    maintenance_logs = db.relationship("MaintenanceLog", back_populates="equipment", cascade="all, delete-orphan")
    owner = db.relationship("User", back_populates="equipments", foreign_keys=[owner_id])  # New relationship
    @property
    def is_available(self):
        return self.status == 'available' and self.current_users < self.max_users
    
    @property
    def needs_maintenance(self):
        if not self.next_maintenance:
            return False
        return datetime.now().date() >= self.next_maintenance
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'equipment_type': self.equipment_type,
            'brand': self.brand,
            'model': self.model,
            'status': self.status,
            'condition': self.condition,
            'location': self.location,
            'is_available': self.is_available,
            'needs_maintenance': self.needs_maintenance,
            'current_users': self.current_users,
            'max_users': self.max_users,
            'specifications': self.specifications or {},
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

