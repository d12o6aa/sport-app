from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(150))
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'admin', 'coach', 'athlete'
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    athletes = db.relationship('User')  # Reverse relation for coach's athletes
  

    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    team = db.Column(db.String(100))
    profile_image = db.Column(db.String(255))
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
