from app.extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime

class Exercise(db.Model):
    __tablename__ = "exercises"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Media
    image_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    gif_url = db.Column(db.String(255))  # for animated demonstrations
    
    # Exercise categorization
    category = db.Column(db.String(50))  # strength, cardio, flexibility, balance
    muscle_groups = db.Column(db.JSON)   # ["chest", "shoulders", "triceps"]
    equipment_needed = db.Column(db.JSON)  # ["dumbbells", "bench"]
    difficulty_level = db.Column(
        db.String(20),
        db.CheckConstraint("difficulty_level IN ('beginner','intermediate','advanced')"),
        default="beginner"
    )
    
    # Default metrics
    default_duration = db.Column(db.Integer)  # in seconds
    estimated_calories_per_minute = db.Column(db.Integer)
    default_sets = db.Column(db.Integer, default=3)
    default_reps = db.Column(db.Integer, default=10)
    
    # Exercise instructions
    instructions = db.Column(db.Text)  # step-by-step instructions
    tips = db.Column(db.Text)  # form tips and safety notes
    modifications = db.Column(db.Text)  # easier/harder variations
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workout_logs = relationship(
        "WorkoutLogExercise",
        back_populates="exercise",
        cascade="all, delete-orphan"
    )
    creator = db.relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        db.Index("idx_exercises_name", "name"),
        db.Index("idx_exercises_category", "category"),
        db.Index("idx_exercises_difficulty", "difficulty_level"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "video_url": self.video_url,
            "gif_url": self.gif_url,
            "category": self.category,
            "muscle_groups": self.muscle_groups or [],
            "equipment_needed": self.equipment_needed or [],
            "difficulty_level": self.difficulty_level,
            "default_duration": self.default_duration,
            "estimated_calories_per_minute": self.estimated_calories_per_minute,
            "default_sets": self.default_sets,
            "default_reps": self.default_reps,
            "instructions": self.instructions,
            "tips": self.tips,
            "modifications": self.modifications,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Exercise {self.name}>"

