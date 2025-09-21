from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB


# ================================
# Enhanced Event Model
# ================================

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    
    # Enhanced event fields
    event_type = db.Column(
        db.String(30),
        db.CheckConstraint("event_type IN ('class','workshop','competition','maintenance','promotion','holiday','announcement')"),
        default='announcement'
    )
    
    # Date and time
    date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    duration_hours = db.Column(db.Integer)  # Duration in hours
    
    # Location and capacity
    location = db.Column(db.String(100))
    max_participants = db.Column(db.Integer)
    current_participants = db.Column(db.Integer, default=0)
    
    # Registration
    requires_registration = db.Column(db.Boolean, default=False)
    registration_deadline = db.Column(db.Date)
    registration_fee = db.Column(db.Float, default=0.0)
    
    # Status
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('scheduled','ongoing','completed','cancelled','postponed')"),
        default='scheduled'
    )
    
    # Organizer and contact
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    
    # Media and resources
    image_url = db.Column(db.String(255))
    attachment_urls = db.Column(JSONB, default=list)  # Multiple attachments
    
    # Notification settings
    send_notifications = db.Column(db.Boolean, default=True)
    notification_sent = db.Column(db.Boolean, default=False)
    reminder_sent = db.Column(db.Boolean, default=False)
    
    # extra_data
    extra_data = db.Column(JSONB, default=dict)  # Additional event-specific data
    tags = db.Column(JSONB, default=list)  # Event tags for filtering
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organizer = db.relationship("User", foreign_keys=[organizer_id], back_populates="events")  # Fixed back_populates
    registrations = db.relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")
    @property
    def is_full(self):
        return self.max_participants and self.current_participants >= self.max_participants
    
    @property
    def registration_open(self):
        if not self.requires_registration:
            return False
        if self.registration_deadline:
            return datetime.now().date() <= self.registration_deadline
        return datetime.now().date() < self.date
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'location': self.location,
            'status': self.status,
            'max_participants': self.max_participants,
            'current_participants': self.current_participants,
            'is_full': self.is_full,
            'registration_open': self.registration_open,
            'requires_registration': self.requires_registration,
            'registration_fee': self.registration_fee,
            'image_url': self.image_url,
            'tags': self.tags or [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
