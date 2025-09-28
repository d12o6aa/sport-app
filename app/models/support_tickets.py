# app/models/support_tickets.py
from datetime import datetime
from app.extensions import db

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium', index=True)  # 'low', 'medium', 'high'
    status = db.Column(db.String(20), default='pending', index=True)  # 'pending', 'in_progress', 'resolved'
    admin_response = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='support_tickets')
    
    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_support_tickets_user_id', 'user_id'),
        db.Index('idx_support_tickets_status_priority', 'status', 'priority'),
        db.Index('idx_support_tickets_created_at', 'created_at'),
        db.CheckConstraint("priority IN ('low', 'medium', 'high')", name='chk_priority'),
        db.CheckConstraint("status IN ('pending', 'in_progress', 'resolved')", name='chk_status'),
    )
    
    def __repr__(self):
        return f'<SupportTicket {self.id}: {self.subject[:50]}...>'
    
    @property
    def user_name(self):
        return self.user.name if self.user else "Anonymous"
    
    @property
    def user_email(self):
        return self.user.email if self.user else "No email"
    
    def mark_resolved(self):
        """Mark the ticket as resolved and set resolved_at timestamp"""
        self.status = 'resolved'
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user': self.user_name,
            'user_email': self.user_email,
            'subject': self.subject,
            'content': self.content,
            'priority': self.priority,
            'status': self.status,
            'admin_response': self.admin_response,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M') if self.resolved_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None
        }