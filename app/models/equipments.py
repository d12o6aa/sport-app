from datetime import datetime
from app.extensions import db

class Equipment(db.Model):
    __tablename__ = "equipments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), nullable=False, default="available")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
