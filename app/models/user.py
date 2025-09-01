from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

USERS_TABLE = "users"


class User(db.Model):
    __tablename__ = USERS_TABLE

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20),
        db.CheckConstraint("role IN ('admin','coach','athlete')"),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(20),
        db.CheckConstraint("status IN ('pending','active','suspended')"),
        default="pending",
        index=True,
    )
    profile_image = db.Column(db.Text, default="default.jpg")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-One profiles
    coach_profile = db.relationship("CoachProfile", uselist=False, back_populates="user")
    athlete_profile = db.relationship("AthleteProfile", uselist=False, back_populates="user")
    admin_profile = db.relationship("AdminProfile", uselist=False, back_populates="user")

    # Logs / files / insights
    activity_logs = db.relationship("ActivityLog", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    subscriptions = db.relationship("Subscription", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    workout_files = db.relationship("WorkoutFile", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")
    workout_logs = db.relationship("WorkoutLog", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")
    readiness_scores = db.relationship("ReadinessScore", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")
    ml_insights = db.relationship("MLInsight", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")

    # Groups
    training_groups = db.relationship("TrainingGroup", back_populates="trainer", lazy="dynamic")  # as trainer/owner
    group_assignments = db.relationship("AthleteGroup", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")

    # Plans
    training_plans = db.relationship("TrainingPlan", back_populates="coach",foreign_keys="TrainingPlan.coach_id", lazy="dynamic", cascade="all, delete-orphan")
    plan_assignments = db.relationship("AthletePlan", back_populates="athlete",foreign_keys="AthletePlan.athlete_id", lazy="dynamic", cascade="all, delete-orphan")

    # Coach <-> Athlete link (ownership / roster)
    athlete_links = db.relationship("CoachAthlete", foreign_keys="[CoachAthlete.coach_id]", back_populates="coach", lazy="dynamic", cascade="all, delete-orphan")
    coach_links = db.relationship("CoachAthlete", foreign_keys="[CoachAthlete.athlete_id]", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")

    # Messaging
    sent_messages = db.relationship("Message", foreign_keys="[Message.sender_id]", back_populates="sender", lazy="dynamic", cascade="all, delete-orphan")
    received_messages = db.relationship("Message", foreign_keys="[Message.receiver_id]", back_populates="receiver", lazy="dynamic", cascade="all, delete-orphan")

    # Athlete Dashboard
    goals = db.relationship("AthleteGoal", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")
    schedule = db.relationship("AthleteSchedule", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")
    progress = db.relationship("AthleteProgress", back_populates="athlete", lazy="dynamic", cascade="all, delete-orphan")

    # Helpers
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    __table_args__ = (
        db.Index("idx_users_email", "email"),
        db.Index("idx_users_role", "role"),
        db.Index("idx_users_status", "status"),
    )
    # ------- helper properties -------
    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_superadmin(self):
        return self.role == "admin" and self.admin_profile and self.admin_profile.is_superadmin


    @property
    def is_coach(self):
        return self.role == "coach"

    @property
    def is_athlete(self):
        return self.role == "athlete"
    
