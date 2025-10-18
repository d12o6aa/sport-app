# ================================
# Enhanced Coach Athlete Management Backend - FINAL
# ================================

import os
from flask import Blueprint, request, jsonify, render_template, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db
from app.models import (
    User, CoachAthlete, TrainingPlan, WorkoutLog,
    ActivityLog, AthleteProgress, AthleteProfile, AthletePlan,
    ReadinessScore, MLInsight
)
from . import coach_bp

# ✅ استيراد مكتبة traceback للحصول على تفاصيل الخطأ
import traceback

# ✅ استيراد pandas و joblib للتعامل مع النموذج الجديد
import pandas as pd
import joblib

# ✅ تحميل نموذج التعلم الآلي مرة واحدة عند بدء التطبيق
# توجيه المسار إلى المجلد الصحيح الذي يحتوي على النموذج
try:
    model_path = os.path.join(os.path.dirname(__file__), '..', 'prediction', 'models', 'injury_severity_pipeline.pkl')
    # طباعة المسار للتأكد من صحته أثناء التطوير
    # print(f"Loading ML model from: {model_path}")
    injury_model = joblib.load(model_path)
    # print("ML model loaded successfully.")
except FileNotFoundError:
    print(f"Error: The model file was not found at {model_path}. Please check the path.")
    injury_model = None
except Exception as e:
    print(f"An error occurred while loading the model: {e}")
    injury_model = None

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# ================================
# Helper function to run ML prediction
# ================================

def run_prediction_service(athlete_id, input_data):
    """
    Runs the injury prediction model and returns the results.
    This function is now a core service called from update_athlete.
    """
    if injury_model is None:
        return {"error": "ML model not loaded"}, 500

    athlete_profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()
    if not athlete_profile:
        return {"error": "Athlete profile not found"}, 404

    # Helper to safely convert incoming data to float/int
    def safe_float(key, default=0.0):
        try:
            value = input_data.get(key)
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_int(key, default=0):
        try:
            value = input_data.get(key)
            if value is None or value == "":
                return default
            return int(float(value)) # Convert float to int safely
        except (ValueError, TypeError):
            return default

    try:
        # Prepare data for the new injury prediction model
        ml_input_df = pd.DataFrame([{
            "Player_Age": safe_int("Player_Age", athlete_profile.age),
            "Player_Weight": safe_float("Player_Weight", athlete_profile.weight),
            "Player_Height": safe_float("Player_Height", athlete_profile.height),
            "Previous_Injuries": safe_int("Previous_Injuries", input_data.get("previous_injuries", 0)),
            "Training_Intensity": safe_float("Training_Intensity", input_data.get("training_intensity", 5.0)),
            "Recovery_Time": safe_float("Recovery_Time", input_data.get("recovery_time", 1.0))
        }])

        # Add required feature engineering steps from the original notebook/script
        # هذه السطور كانت سبب الخطأ
        ml_input_df['Player_Weight'] = ml_input_df['Player_Weight'].round(2)
        ml_input_df['Player_Height'] = ml_input_df['Player_Height'].round(2)
        ml_input_df['Training_Intensity'] = ml_input_df['Training_Intensity'].round(2)

        # بعد التأكد من أن جميع القيم رقمية، يمكن إجراء العملية الحسابية
        ml_input_df['BMI'] = ml_input_df['Player_Weight'] / (ml_input_df['Player_Height'] / 100) ** 2

        gaps = [-float('inf'), 18.5, 24.9, 29.9, 34.9, 39.9, float('inf')]
        categories = ['Underweight', 'Normal', 'Overweight', 'Obesity I', 'Obesity II', 'Obesity III']
        ml_input_df['BMI_Classification'] = pd.cut(ml_input_df['BMI'], bins=gaps, labels=categories, right=False)

        ml_input_df["Age_Group"] = pd.cut(
            ml_input_df["Player_Age"],
            bins=[18, 22, 26, 30, 34, 100],
            labels=["18-22", "23-26", "27-30", "31-34", "35+"],
            include_lowest=True,
        )

        for col in ['Normal', 'Obesity I', 'Obesity II', 'Overweight', 'Underweight']:
            ml_input_df[f'BMI_Classification_{col}'] = (ml_input_df['BMI_Classification'] == col).astype(int)

        for group in ['18-22', '23-26', '27-30', '31-34', '35+']:
            ml_input_df[f'Age_Group_{group}'] = (ml_input_df['Age_Group'] == group).astype(int)

        ml_input_df.drop(columns=['BMI_Classification', 'Age_Group'], inplace=True)
        
        # Run prediction with the new model
        prediction_result = injury_model.predict(ml_input_df)[0]
        probability = injury_model.predict_proba(ml_input_df)[0][1]

        injury_risk_label = "High" if prediction_result == 1 else "Low"
        readiness_score = 100 - (probability * 100) # Simple heuristic for readiness

        return {
            "injury_risk": injury_risk_label,
            "injury_probability": float(probability),
            "readiness_score": int(readiness_score)
        }, 200

    except Exception as e:
        print("--- PREDICTION SERVICE ERROR ---")
        print(f"Error Details: {str(e)}")
        print(f"Input Data: {input_data}")
        print("Traceback:")
        print(traceback.format_exc())
        return {"error": "An error occurred during prediction service."}, 500
# ================================
# Main Management Page
# ================================
@coach_bp.route("/manage_athletes", methods=["GET"])
@jwt_required()
def manage_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    return render_template("coach/manage_athletes.html")

# ================================
# Get All Athletes
# ================================
@coach_bp.route("/athletes", methods=["GET"])
@jwt_required()
def get_coach_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        linked_athletes = CoachAthlete.query.filter_by(coach_id=identity).all()

        athlete_list = []
        for link in linked_athletes:
            user = User.query.get(link.athlete_id)
            if not user or user.is_deleted:
                continue

            profile = AthleteProfile.query.filter_by(user_id=user.id).first()

            workout_stats = db.session.query(
                func.max(WorkoutLog.logged_at).label('last_workout'),
                func.count(WorkoutLog.id).label('total_workouts'),
                func.sum(
                    db.case(
                        (WorkoutLog.completion_status == 'completed', 1),
                        else_=0
                    )
                ).label('completed_workouts')
            ).filter(WorkoutLog.athlete_id == user.id).first()

            last_workout = workout_stats.last_workout
            total_workouts = workout_stats.total_workouts or 0
            completed_workouts = workout_stats.completed_workouts or 0

            compliance = 0
            if total_workouts > 0:
                compliance = round((completed_workouts / total_workouts) * 100, 1)

            readiness_score = None
            injury_risk = "unknown"

            # ✅ ابحث أولاً في جدول MLInsight
            latest_ml_insight = MLInsight.query.filter_by(
                athlete_id=user.id
            ).order_by(desc(MLInsight.generated_at)).first()

            if latest_ml_insight:
                readiness_score = latest_ml_insight.insight_data.get('readiness_score')
                injury_risk = latest_ml_insight.insight_data.get('injury_risk')
            else:
                # إذا لم يتم العثور على سجل في MLInsight، ابحث في ReadinessScore
                latest_readiness = ReadinessScore.query.filter_by(
                    athlete_id=user.id
                ).order_by(desc(ReadinessScore.date)).first()
                if latest_readiness:
                    readiness_score = latest_readiness.score
                    injury_risk = latest_readiness.injury_risk
                else:
                    readiness_score = "N/A"
                    injury_risk = "No Data"


            if last_workout:
                time_diff = datetime.utcnow() - last_workout
                if time_diff.days == 0:
                    if time_diff.seconds < 3600:
                        last_activity = f"{time_diff.seconds // 60} minutes ago"
                    else:
                        last_activity = f"{time_diff.seconds // 3600} hours ago"
                elif time_diff.days == 1:
                    last_activity = "1 day ago"
                elif time_diff.days < 7:
                    last_activity = f"{time_diff.days} days ago"
                else:
                    last_activity = f"{time_diff.days // 7} weeks ago"
            else:
                last_activity = "N/A"

            profile_image_url = url_for('static', filename='uploads/profile/' + (user.profile_image or 'default.jpeg'))

            athlete_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "is_active": link.is_active,
                "last_activity": last_activity,
                "compliance": compliance,
                "total_workouts": total_workouts,
                "completed_workouts": completed_workouts,
                "readiness_score": readiness_score,
                "injury_risk": injury_risk,
                "profile_image": profile_image_url,
                "assigned_at": link.assigned_at.strftime("%Y-%m-%d") if link.assigned_at else None
            })

        return jsonify(athlete_list)

    except Exception as e:
        print(f"FATAL ERROR in get_coach_athletes: {traceback.format_exc()}")
        return jsonify({"msg": f"An error occurred: {str(e)}"}), 500

# ================================
# Get Detailed Athlete Information (FINAL)
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/details", methods=["GET"])
@jwt_required()
def get_athlete_details(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()

    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()

    latest_ml_insight = MLInsight.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(MLInsight.generated_at)).first()

    ml_data = latest_ml_insight.insight_data if latest_ml_insight else {}

    latest_readiness = ReadinessScore.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(ReadinessScore.date)).first()

    workout_stats = db.session.query(
        func.count(WorkoutLog.id).label('total'),
        func.sum(
            db.case(
                (WorkoutLog.completion_status == 'completed', 1),
                else_=0
            )
        ).label('completed')
    ).filter(
        WorkoutLog.athlete_id == athlete_id
    ).first()

    total_workouts = workout_stats[0] or 0
    completed_workouts = workout_stats[1] or 0
    compliance = 0
    if total_workouts > 0:
        compliance = round((completed_workouts / total_workouts) * 100, 1)

    last_workout = WorkoutLog.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(WorkoutLog.logged_at)).first()

    if last_workout:
        time_diff = datetime.utcnow() - last_workout.logged_at
        if time_diff.days == 0:
            last_activity = f"{time_diff.seconds // 3600} hours ago"
        else:
            last_activity = f"{time_diff.days} days ago"
    else:
        last_activity = "No recent activity"

    recent_activities = get_recent_activities(athlete_id)
    
    profile_image_url = url_for('static', filename='uploads/profile/' + (athlete.profile_image or 'default.jpeg'))

    # ✅ تم إضافة الحقول الجديدة إلى الـ JSON response
    return jsonify({
        "id": athlete.id,
        "name": athlete.name,
        "email": athlete.email,
        "status": athlete.status,
        "profile_image": profile_image_url,
        "age": profile.age if profile else None,
        "gender": profile.gender if profile else None,
        "weight": profile.weight if profile else None,
        "height": profile.height if profile else None,
        "team": profile.team if profile else None,
        "position": profile.position if profile else None,
        "previous_injuries": profile.previous_injuries if profile else None, # ✅ جديد
        "training_intensity": profile.training_intensity if profile else None, # ✅ جديد
        "recovery_time": profile.recovery_time if profile else None, # ✅ جديد
        "compliance": compliance,
        "total_workouts": total_workouts,
        "completed_workouts": completed_workouts,
        "last_activity": last_activity,
        "recent_activities": recent_activities,
        "ml_insights": {
            "injury_severity": ml_data.get("injury_risk") if ml_data else "No Data",
            "injury_probability": ml_data.get("injury_probability") if ml_data else "No Data",
            "readiness_score": ml_data.get("readiness_score") if ml_data else "No Data"
        },
        "readiness": {
            "score": latest_readiness.score if latest_readiness else None,
            "injury_risk": latest_readiness.injury_risk if latest_readiness else "No Data",
            "recovery_prediction": latest_readiness.recovery_prediction if latest_readiness else None,
            "date": latest_readiness.date.isoformat() if latest_readiness else None
        }
    })
# ================================
# Update Athlete Profile (now includes ML data)
# ================================
@coach_bp.route("/athlete/<int:athlete_id>", methods=["PUT"])
@jwt_required()
def update_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()

    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.get_json()
    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()

    if not profile:
        profile = AthleteProfile(user_id=athlete_id)
        db.session.add(profile)

    try:
        # Update User data
        if data.get("name"):
            athlete.name = data.get("name")
        if data.get("email"):
            existing = User.query.filter(
                User.email == data.get("email"),
                User.id != athlete_id
            ).first()
            if existing:
                return jsonify({"msg": "Email already in use"}), 400
            athlete.email = data.get("email")

        # Update AthleteProfile data
        profile.age = data.get("age")
        profile.gender = data.get("gender")
        profile.weight = data.get("weight")
        profile.height = data.get("height")
        profile.team = data.get("team")
        profile.position = data.get("position")

        # Update ML-specific data
        profile.previous_injuries = data.get("previous_injuries", profile.previous_injuries)
        profile.training_intensity = data.get("training_intensity", profile.training_intensity)
        profile.recovery_time = data.get("recovery_time", profile.recovery_time)

        # ✅ Run ML prediction automatically
        prediction_input = {
            "Previous_Injuries": profile.previous_injuries,
            "Training_Intensity": profile.training_intensity,
            "Recovery_Time": profile.recovery_time,
            "Player_Age": profile.age,
            "Player_Weight": profile.weight,
            "Player_Height": profile.height
        }
        
        # Check if we have enough data to run the prediction
        if (
            prediction_input["Previous_Injuries"] is not None and
            prediction_input["Training_Intensity"] is not None and
            prediction_input["Recovery_Time"] is not None and
            profile.age is not None and
            profile.weight is not None and
            profile.height is not None
        ):
            print("Running automatic prediction after profile update...")
            ml_result, status_code = run_prediction_service(athlete_id, prediction_input)
            
            if status_code == 200:
                # Store new MLInsight
                insight = MLInsight(
                    athlete_id=athlete_id,
                    generated_at=datetime.utcnow(),
                    insight_data=ml_result
                )
                db.session.add(insight)

                # Store Readiness Score
                rs = ReadinessScore(
                    athlete_id=athlete_id,
                    date=datetime.utcnow().date(),
                    score=ml_result.get("readiness_score"),
                    injury_risk=ml_result.get("injury_risk"),
                    recovery_prediction="N/A"
                )
                db.session.add(rs)
                print("Prediction results stored successfully.")
            else:
                print(f"Prediction service failed with error: {ml_result.get('error')}")
                # Log the error but don't fail the entire update process
        else:
            print("Not enough data to run a full prediction yet.")

        # Log the activity
        activity = ActivityLog(
            user_id=identity,
            action="Updated athlete profile",
            details={"athlete_id": athlete_id, "athlete_name": athlete.name},
            created_at=datetime.utcnow()
        )
        db.session.add(activity)

        db.session.commit()
        return jsonify({"msg": "Athlete updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("--- FATAL UPDATE ATHLETE ERROR ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        print("-------------------------------------")
        return jsonify({"msg": f"Error updating athlete: {str(e)}"}), 500

# ================================
# Other routes (unchanged)
# ================================
@coach_bp.route("/athlete/<int:athlete_id>", methods=["DELETE"])
@jwt_required()
def delete_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    try:
        link.is_active = False
        link.status = "unassigned"
        athlete = User.query.get(athlete_id)
        activity = ActivityLog(
            user_id=identity,
            action="Unassigned athlete",
            details={"athlete_id": athlete_id, "athlete_name": athlete.name if athlete else "Unknown"},
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({"msg": "Athlete unassigned successfully. Admin can reassign to another coach.","status": "unassigned"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error unassigning athlete: {str(e)}"}), 500

@coach_bp.route("/athlete/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_athlete_progress(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    start_date = datetime.utcnow() - timedelta(days=30)
    progress_data = AthleteProgress.query.filter(
        AthleteProgress.athlete_id == athlete_id,
        AthleteProgress.date >= start_date
    ).order_by(desc(AthleteProgress.date)).all()
    readiness_data = ReadinessScore.query.filter(
        ReadinessScore.athlete_id == athlete_id,
        ReadinessScore.date >= start_date.date()
    ).order_by(desc(ReadinessScore.date)).all()
    dates = []
    weights = []
    workouts = []
    readiness_scores = []
    injury_risks = []
    progress_map = {p.date.strftime("%b %d"): p for p in progress_data}
    readiness_map = {r.date.strftime("%b %d"): r for r in readiness_data}
    all_dates = sorted(list(set(progress_map.keys()) | set(readiness_map.keys())))
    for date_str in all_dates:
        p = progress_map.get(date_str)
        r = readiness_map.get(date_str)
        dates.append(date_str)
        weights.append(float(p.weight) if p and p.weight else None)
        workouts.append(p.workouts_done or 0 if p else 0)
        readiness_scores.append(r.score if r else None)
        risk_map = {"low": 1, "Low": 1, "medium": 2, "Medium": 2, "high": 3, "High": 3}
        injury_risks.append(risk_map.get(r.injury_risk, 0) if r else 0)
    return jsonify({
        "dates": dates,
        "weights": weights,
        "workouts": workouts,
        "readiness_scores": readiness_scores,
        "injury_risks": injury_risks
    })

@coach_bp.route("/athlete/<int:athlete_id>/stats", methods=["GET"])
@jwt_required()
def get_athlete_stats(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        workout_stats = db.session.query(
            func.count(WorkoutLog.id).label('total'),
            func.sum(db.case((WorkoutLog.completion_status == 'completed', 1), else_=0)).label('completed'),
            func.sum(WorkoutLog.calories_burned).label('total_calories'),
            func.sum(WorkoutLog.actual_duration).label('total_duration')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= start_date.date()
        ).first()
        latest_progress = AthleteProgress.query.filter_by(athlete_id=athlete_id).order_by(desc(AthleteProgress.date)).first()
        latest_ml = MLInsight.query.filter_by(athlete_id=athlete_id).order_by(desc(MLInsight.generated_at)).first()
        ml_data = latest_ml.insight_data if latest_ml else {}
        latest_readiness = ReadinessScore.query.filter_by(athlete_id=athlete_id).order_by(desc(ReadinessScore.date)).first()
        active_plans_count = db.session.query(func.count(TrainingPlan.id)).join(
            AthletePlan, AthletePlan.plan_id == TrainingPlan.id
        ).filter(
            AthletePlan.athlete_id == athlete_id,
            TrainingPlan.status == 'active'
        ).scalar()
        return jsonify({
            "workout_stats": {
                "total_workouts": workout_stats[0] or 0,
                "completed_workouts": workout_stats[1] or 0,
                "total_calories": int(workout_stats[2] or 0),
                "total_duration": int(workout_stats[3] or 0)
            },
            "current_progress": {
                "weight": float(latest_progress.weight) if latest_progress and latest_progress.weight else None,
                "bmi": float(latest_progress.bmi) if latest_progress and latest_progress.bmi else None,
                "body_fat": float(latest_progress.body_fat) if latest_progress and latest_progress.body_fat else None
            },
            "ml_insights": {
                "injury_severity": ml_data.get("injury_risk"),
                "injury_probability": ml_data.get("injury_probability"),
                "readiness_score": ml_data.get("readiness_score"),
                "generated_at": latest_ml.generated_at.isoformat() if latest_ml else None
            },
            "readiness": {
                "score": latest_readiness.score if latest_readiness else None,
                "injury_risk": latest_readiness.injury_risk if latest_readiness else None,
                "recovery_prediction": latest_readiness.recovery_prediction if latest_readiness else None
            },
            "active_plans": active_plans_count or 0,
            "period_days": days
        })
    except Exception as e:
        return jsonify({"msg": f"Error retrieving stats: {str(e)}"}), 500

# ================================
# Helper Functions (unchanged)
# ================================
def get_recent_activities(athlete_id, limit=5):
    activities = []
    recent_workouts = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(desc(WorkoutLog.logged_at)).limit(limit).all()
    for workout in recent_workouts:
        time_ago = format_time_ago(workout.logged_at)
        activities.append({"icon": "bi-check-circle","description": f"Completed workout: {workout.title or 'Training Session'}","timestamp": time_ago})
    return activities

def format_time_ago(dt):
    if not dt: return "Unknown"
    time_diff = datetime.utcnow() - dt
    if time_diff.days == 0:
        if time_diff.seconds < 3600: return f"{time_diff.seconds // 60} minutes ago"
        else: return f"{time_diff.seconds // 3600} hours ago"
    elif time_diff.days == 1: return "Yesterday"
    elif time_diff.days < 7: return f"{time_diff.days} days ago"
    else: return dt.strftime("%b %d, %Y")
    
# Get basic athlete data (for modal population)
@coach_bp.route("/athlete/<int:athlete_id>", methods=["GET"])
@jwt_required()
def get_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()
    return jsonify({
        "id": athlete.id,
        "name": athlete.name,
        "email": athlete.email,
        "age": profile.age if profile else None,
        "gender": profile.gender if profile else None,
        "weight": profile.weight if profile else None,
        "height": profile.height if profile else None,
        "team": profile.team if profile else None,
        "position": profile.position if profile else None,
        "previous_injuries": profile.previous_injuries if profile else None,
        "training_intensity": profile.training_intensity if profile else None,
        "recovery_time": profile.recovery_time if profile else None,
    })

# Add athlete (unchanged)
@coach_bp.route("/athlete/add", methods=["POST"])
@jwt_required()
def add_athlete():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    data = request.get_json()
    required_fields = ["name", "email", "password"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"msg": f"Missing required field: {field}"}), 400
    if User.query.filter_by(email=data.get("email")).first():
        return jsonify({"msg": "Email already registered"}), 400
    try:
        new_athlete = User(
            name=data.get("name"),
            email=data.get("email"),
            password_hash=generate_password_hash(data.get("password")),
            role="athlete",
            status="active",
            created_at=datetime.utcnow()
        )
        db.session.add(new_athlete)
        db.session.flush()
        profile = AthleteProfile(
            user_id=new_athlete.id,
            age=data.get("age"),
            gender=data.get("gender"),
            weight=data.get("weight"),
            height=data.get("height"),
            team=data.get("team"),
            position=data.get("position")
        )
        db.session.add(profile)
        link = CoachAthlete(
            coach_id=identity,
            athlete_id=new_athlete.id,
            assigned_at=datetime.utcnow(),
            status="approved",
            is_active=True
        )
        db.session.add(link)
        activity = ActivityLog(
            user_id=identity,
            action="Added new athlete",
            details={"athlete_id": new_athlete.id, "athlete_name": new_athlete.name},
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({"msg": "Athlete added successfully", "athlete_id": new_athlete.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error adding athlete: {str(e)}"}), 500

@coach_bp.route("/athlete/<int:athlete_id>/workouts", methods=["GET"])
@jwt_required()
def get_athlete_workouts(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    workouts = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(desc(WorkoutLog.logged_at)).limit(10).all()
    workout_list = []
    for workout in workouts:
        workout_list.append({
            "id": workout.id,
            "title": workout.title or "Workout",
            "date": workout.date.strftime("%Y-%m-%d") if workout.date else None,
            "duration": workout.actual_duration or workout.planned_duration,
            "calories_burned": workout.calories_burned,
            "completion_status": workout.completion_status,
            "workout_type": workout.workout_type
        })
    return jsonify(workout_list)

@coach_bp.route("/athlete/<int:athlete_id>/plans", methods=["GET"])
@jwt_required()
def get_athlete_plans(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403
    link = CoachAthlete.query.filter_by(coach_id=identity, athlete_id=athlete_id).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403
    plans = db.session.query(TrainingPlan).join(AthletePlan, AthletePlan.plan_id == TrainingPlan.id).filter(
        AthletePlan.athlete_id == athlete_id
    ).all()
    plan_list = []
    for plan in plans:
        plan_list.append({
            "id": plan.id,
            "title": plan.title,
            "start_date": plan.start_date.strftime("%Y-%m-%d"),
            "end_date": plan.end_date.strftime("%Y-%m-%d"),
            "status": plan.status,
            "description": plan.description
        })
    return jsonify(plan_list)