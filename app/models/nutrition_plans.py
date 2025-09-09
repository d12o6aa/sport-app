from datetime import datetime
from app.extensions import db

class NutritionPlan(db.Model):
    __tablename__ = "nutrition_plans"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("training_plans.id"), nullable=False)
    calories_intake = db.Column(db.Integer)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    athlete = db.relationship("User", back_populates="nutrition_plans")
    plan = db.relationship("TrainingPlan", back_populates="nutrition")
