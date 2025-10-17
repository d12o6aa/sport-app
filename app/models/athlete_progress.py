
# app/models/athlete_progress.py
from app.extensions import db
from datetime import datetime

class AthleteProgress(db.Model):
    __tablename__ = 'athlete_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    
    # Basic Health Metrics
    weight = db.Column(db.Float)
    weight_goal = db.Column(db.Float)
    bmi = db.Column(db.Float)
    body_fat = db.Column(db.Float)
    muscle_mass = db.Column(db.Float)
    heart_rate = db.Column(db.Integer)
    
    # Workout Statistics
    workouts_done = db.Column(db.Integer, default=0)
    calories_burned = db.Column(db.Integer, default=0)
    
    # Nutrition (optional)
    protein = db.Column(db.Integer)
    carbs = db.Column(db.Integer)
    fats = db.Column(db.Integer)
    
    # ✅ NEW: Calculated Progress Scores for ML Training
    workout_score = db.Column(db.Float, default=0)  # 0-100
    goals_completion_rate = db.Column(db.Float, default=0)  # 0-100
    plan_adherence = db.Column(db.Float, default=0)  # 0-100
    consistency_score = db.Column(db.Float, default=0)  # 0-100
    overall_health_score = db.Column(db.Float, default=0)  # 0-100
    completed_goals = db.Column(db.Integer, default=0)  # ✅ New field to track number of completed goals
    total_goals = db.Column(db.Integer, default=0)      # ✅ New field to track total number of goals
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    avg_goal_progress = db.Column(db.Float, default=0)  # ✅ New field to track average goal progress percentage
    plan_adherence = db.Column(db.Float, default=0)  # ✅ New field to track plan adherence percentage
    consistency_score = db.Column(db.Float, default=0)  # ✅ New field to track consistency score percentage
    health_score = db.Column(db.Float, default=0)  # ✅ New field to track overall health score percentage
    
    # Relationship
    athlete = db.relationship("User", back_populates="progress")
    
    def to_dict(self):
        return {
            'id': self.id,
            'athlete_id': self.athlete_id,
            'date': self.date.isoformat(),
            'weight': self.weight,
            'weight_goal': self.weight_goal,
            'bmi': self.bmi,
            'body_fat': self.body_fat,
            'muscle_mass': self.muscle_mass,
            'heart_rate': self.heart_rate,
            'workouts_done': self.workouts_done,
            'calories_burned': self.calories_burned,
            'protein': self.protein,
            'carbs': self.carbs,
            'fats': self.fats,
            'workout_score': self.workout_score,
            'goals_completion_rate': self.goals_completion_rate,
            'plan_adherence': self.plan_adherence,
            'consistency_score': self.consistency_score,
            'overall_health_score': self.overall_health_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
