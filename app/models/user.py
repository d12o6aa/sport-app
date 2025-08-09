from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Boolean, JSON


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(150))
    is_active = db.Column(db.Boolean, default=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False)

    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # هنا العلاقة الصحيحة
    coach = db.relationship('User', remote_side=[id], backref='athletes', foreign_keys=[coach_id])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_superadmin = db.Column(db.Boolean, default=False)
    permissions = db.Column(db.JSON, default=[])
    # inside User model
    
    plans = db.relationship('TrainingPlan', back_populates='coach', lazy='dynamic')
    assigned_plans = db.relationship('PlanAssignment', back_populates='athlete', lazy='dynamic')


    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    team = db.Column(db.String(100))
    profile_image = db.Column(db.String(255), default='default.jpg')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
