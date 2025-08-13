from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB

class AdminProfile(db.Model):
    __tablename__ = "admin_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    permissions = db.Column(JSONB, server_default='{"can_create_admins": true, "can_manage_users": true, "can_export_data": true}', default=lambda: {
        "can_create_admins": True,
        "can_manage_users": True,
        "can_export_data": True,
    })

    user = db.relationship("User", back_populates="admin_profile")
