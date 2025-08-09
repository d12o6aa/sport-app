# app/models/training.py
from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Boolean, JSON
class TrainingPlan(db.Model):
    __tablename__ = 'training_plan'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    coach_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    coach = db.relationship('User', back_populates='plans')
    workouts = db.relationship('Workout', back_populates='plan', cascade='all, delete-orphan')
    assignments = db.relationship('PlanAssignment', back_populates='plan', cascade='all, delete-orphan')

class Workout(db.Model):
    __tablename__ = 'workout'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('training_plan.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, nullable=True)

    plan = db.relationship('TrainingPlan', back_populates='workouts')

class PlanAssignment(db.Model):
    __tablename__ = 'plan_assignment'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('training_plan.id'), nullable=False)
    athlete_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='assigned')  # assigned / completed / cancelled

    plan = db.relationship('TrainingPlan', back_populates='assignments')
    athlete = db.relationship('User', back_populates='assigned_plans')
