# app/models/exercise.py
from app.extensions import db
from sqlalchemy.orm import relationship

class Exercise(db.Model):
    __tablename__ = "exercises"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    duration = db.Column(db.Integer) # in seconds or minutes
    calories = db.Column(db.Integer)
    # يمكنك إضافة حقول أخرى مثل equipment_needed, muscle_group, etc.
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    # علاقات مع جداول أخرى إذا لزم الأمر 
    
    __table_args__ = (
        db.Index("idx_exercises_name", "name"),
    )
    def __repr__(self):
        return f"<Exercise {self.name}>"
    
    
    workout_logs = relationship(
        "WorkoutLogExercise",
        back_populates="exercise",
        cascade="all, delete-orphan"
    )


    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image_url": self.image_url,
            "video_url": self.video_url,
        }