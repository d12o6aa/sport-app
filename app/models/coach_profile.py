from app.extensions import db

class CoachProfile(db.Model):
    __tablename__ = "coach_profiles"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    sport_type = db.Column(db.String(100))
    experience_years = db.Column(db.Integer)
    certifications = db.Column(db.Text)

    user = db.relationship("User", back_populates="coach_profile")
