from app.extensions import db

class WorkoutLogExercise(db.Model):
    __tablename__ = "workout_log_exercises"

    id = db.Column(db.Integer, primary_key=True)
    workout_log_id = db.Column(db.Integer, db.ForeignKey("workout_logs.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"), nullable=False)
    
    # تفاصيل الأداء
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    duration_minutes = db.Column(db.Integer)

    # تحديد العلاقات
    workout_log = db.relationship("WorkoutLog", back_populates="exercises")
    exercise = db.relationship("Exercise", back_populates="workout_logs")

    def __repr__(self):
        return f"<WorkoutLogExercise {self.workout_log_id}-{self.exercise_id}>"