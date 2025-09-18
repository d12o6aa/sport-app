from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from app.extensions import db

class MLInsight(db.Model):
    __tablename__ = "ml_insights"

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    insight_data = db.Column(JSONB, server_default="{}", default=dict)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    athlete = db.relationship("User", back_populates="ml_insights")

    __table_args__ = (
        db.Index("idx_ml_insights_athlete_id", "athlete_id"),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "athlete_id": self.athlete_id,
            "generated_at": self.generated_at.isoformat(),
            "insight_data": self.insight_data
        }
