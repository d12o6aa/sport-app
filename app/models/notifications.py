# ================================
# Enhanced Notification Model
# ================================

from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    coach_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    # Enhanced notification fields
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(
        db.String(20), 
        db.CheckConstraint("type IN ('message','video','alert','event','equipment','training_plan','maintenance','promotion','general')"), 
        nullable=False
    )
    
    # Priority and category
    priority = db.Column(
        db.String(10),
        db.CheckConstraint("priority IN ('low','medium','high','urgent')"),
        default='medium'
    )
    category = db.Column(db.String(50), default='general')
    
    # Media and attachments
    file_path = db.Column(db.String(255))  # For videos/images
    action_url = db.Column(db.String(255))  # URL to redirect to
    extra_data = db.Column(JSONB, default=dict)  # Additional data
    
    # Status and timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    is_read = db.Column(db.Boolean, default=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # For temporary notifications
    
    # Delivery tracking
    delivery_status = db.Column(
        db.String(20),
        db.CheckConstraint("delivery_status IN ('pending','sent','delivered','failed')"),
        default='sent'
    )
    delivery_attempts = db.Column(db.Integer, default=0)
    
    # Relationships
    coach = db.relationship("User", foreign_keys=[coach_id], back_populates="sent_notifications")
    athlete = db.relationship("User", foreign_keys=[athlete_id], back_populates="received_notifications")

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'type': self.type,
            'priority': self.priority,
            'category': self.category,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'is_read': self.is_read,
            'action_url': self.action_url,
            'extra_data': self.extra_data or {},
            'coach_name': self.coach.name if self.coach else 'System',
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

    __table_args__ = (
        db.Index("idx_notifications_coach_athlete", "coach_id", "athlete_id"),
        db.Index("idx_notifications_type_priority", "type", "priority"),
        db.Index("idx_notifications_sent_at", "sent_at"),
    )
