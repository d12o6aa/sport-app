from flask import Blueprint, jsonify, render_template, request, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc, or_
from datetime import datetime
from app import db
from app.models import (
    User, CoachAthlete, WorkoutLog,
    ReadinessScore, TrainingPlan, AthleteProfile,
    ActivityLog, MLInsight
)
import traceback

from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

@coach_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Get all linked athletes
        linked_athletes = CoachAthlete.query.filter_by(coach_id=identity).all()
        athlete_ids = [link.athlete_id for link in linked_athletes]

        # Calculate overall team stats
        total_athletes_count = len(athlete_ids)
        active_athletes_count = CoachAthlete.query.filter_by(coach_id=identity, is_active=True).count()
        
        # Average Readiness from MLInsight or ReadinessScore
        readiness_scores = []
        for athlete_id in athlete_ids:
            # Check MLInsight first
            latest_ml_insight = MLInsight.query.filter_by(
                athlete_id=athlete_id
            ).order_by(desc(MLInsight.generated_at)).first()

            if latest_ml_insight:
                readiness_score = latest_ml_insight.insight_data.get('readiness_score')
                if readiness_score is not None:
                    readiness_scores.append(readiness_score)
            else:
                # If no MLInsight, check ReadinessScore
                latest_readiness = ReadinessScore.query.filter_by(
                    athlete_id=athlete_id
                ).order_by(desc(ReadinessScore.date)).first()
                if latest_readiness and latest_readiness.score is not None:
                    readiness_scores.append(latest_readiness.score)
        
        avg_readiness = round(sum(readiness_scores) / len(readiness_scores), 1) if readiness_scores else "N/A"
        
        # Total workouts
        total_workouts_count = db.session.query(func.count(WorkoutLog.id)).filter(
            WorkoutLog.athlete_id.in_(athlete_ids)
        ).scalar() or 0
        
        # Total plans
        total_plans_count = db.session.query(func.count(TrainingPlan.id)).filter(
            TrainingPlan.coach_id == identity
        ).scalar() or 0

        # Team completion rate
        workout_stats = db.session.query(
            func.count(WorkoutLog.id).label('total'),
            func.sum(
                db.case(
                    (WorkoutLog.completion_status == 'completed', 1),
                    else_=0
                )
            ).label('completed')
        ).filter(WorkoutLog.athlete_id.in_(athlete_ids)).first()
        
        total_workouts = workout_stats.total or 0
        completed_workouts = workout_stats.completed or 0
        team_completion_rate = 0
        if total_workouts > 0:
            team_completion_rate = round((completed_workouts / total_workouts) * 100, 1)

        # Find athletes needing attention
        attention_needed_athletes = []
        
        for athlete_id in athlete_ids:
            athlete = User.query.get(athlete_id)
            if not athlete:
                continue
            
            readiness_score = None
            injury_risk = "No Data"
            
            # Check MLInsight first
            latest_ml_insight = MLInsight.query.filter_by(
                athlete_id=athlete_id
            ).order_by(desc(MLInsight.generated_at)).first()

            if latest_ml_insight:
                readiness_score = latest_ml_insight.insight_data.get('readiness_score')
                injury_risk = latest_ml_insight.insight_data.get('injury_risk')
            else:
                # Check ReadinessScore
                latest_readiness = ReadinessScore.query.filter_by(
                    athlete_id=athlete_id
                ).order_by(desc(ReadinessScore.date)).first()
                if latest_readiness:
                    readiness_score = latest_readiness.score
                    injury_risk = latest_readiness.injury_risk
            
            # Add to attention list if low readiness or high risk
            needs_attention = False
            if readiness_score is not None and readiness_score < 70:
                needs_attention = True
            if injury_risk == 'High':
                needs_attention = True
            
            if needs_attention:
                attention_needed_athletes.append({
                    "id": athlete.id,
                    "name": athlete.name,
                    "readiness_score": readiness_score if readiness_score is not None else "No Data",
                    "injury_risk": injury_risk if injury_risk else "No Data",
                })
        
        # Recent activities (last 5 activities from ActivityLog)
        recent_activities_query = ActivityLog.query.filter_by(
            user_id=identity
        ).order_by(desc(ActivityLog.created_at)).limit(5).all()
        
        recent_activities = []
        for activity in recent_activities_query:
            time_diff = datetime.utcnow() - activity.created_at
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    time_ago = f"{time_diff.seconds // 60}m ago"
                else:
                    time_ago = f"{time_diff.seconds // 3600}h ago"
            elif time_diff.days == 1:
                time_ago = "1d ago"
            else:
                time_ago = f"{time_diff.days}d ago"
            
            # Determine activity type
            action_lower = activity.action.lower()
            if "added" in action_lower or "created" in action_lower:
                activity_type = "success"
            elif "updated" in action_lower or "modified" in action_lower:
                activity_type = "primary"
            elif "deleted" in action_lower or "removed" in action_lower:
                activity_type = "danger"
            else:
                activity_type = "info"
            
            recent_activities.append({
                "time_ago": time_ago,
                "message": activity.action,
                "type": activity_type
            })
        

        return render_template(
            "dashboard/coach_dashboard.html",
            total_athletes=total_athletes_count,
            active_athletes=active_athletes_count,
            avg_readiness=avg_readiness,
            total_workouts=total_workouts_count,
            total_plans=total_plans_count,
            attention_needed_athletes=attention_needed_athletes,
            team_completion_rate=team_completion_rate,
            recent_activities=recent_activities
        )

    except Exception as e:
        print(f"FATAL ERROR in coach_dashboard: {e}")
        print(traceback.format_exc())
        return jsonify({"msg": "An error occurred while loading dashboard data."}), 500