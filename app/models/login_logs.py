# app/models/login_logs.py
from datetime import datetime
from app.extensions import db

class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True)  # 'success', 'failed'
    is_suspicious = db.Column(db.Boolean, default=False, index=True)
    user_agent = db.Column(db.Text, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = db.relationship("User", back_populates="login_logs")
    
    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_login_logs_user_id', 'user_id'),
        db.Index('idx_login_logs_ip_status', 'ip_address', 'status'),
        db.Index('idx_login_logs_created_at', 'created_at'),
        db.Index('idx_login_logs_suspicious', 'is_suspicious'),
    )
    
    def __repr__(self):
        return f'<LoginLog {self.id}: {self.user_id} - {self.status}>'
    
    @property
    def user_name(self):
        return self.user.name if self.user else "Unknown User"
    
    @property
    def user_email(self):
        return self.user.email if self.user else "Unknown Email"
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_email': self.user_email,
            'ip_address': self.ip_address,
            'status': self.status,
            'is_suspicious': self.is_suspicious,
            'user_agent': self.user_agent,
            'details': self.details,
            'timestamp': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

