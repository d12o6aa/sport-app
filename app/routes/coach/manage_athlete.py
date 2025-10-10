# ================================
# Enhanced Coach Athlete Management Backend - FINAL
# ================================

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

# ✅ استيراد دالة التنبؤ من service.py
from app.routes.prediction.service import predict_all

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

# ================================
# Helper function to prepare ML data
# ================================

def get_ml_input_data(athlete_id):
    """
    Collects real data from the database to be used as input for the ML model.
    This function primarily serves as a base to provide defaults when manual input is missing.
    """
    latest_workout = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(desc(WorkoutLog.logged_at)).first()
    latest_progress = AthleteProgress.query.filter_by(athlete_id=athlete_id).order_by(desc(AthleteProgress.date)).first()
    latest_readiness = ReadinessScore.query.filter_by(athlete_id=athlete_id).order_by(desc(ReadinessScore.date)).first()

    # NOTE: The keys must exactly match the model features
    input_data = {
        # General athlete data
        "heart_rate": getattr(latest_workout, 'avg_heart_rate', 0), # Corrected here
        "sleep_hours": getattr(latest_readiness, 'sleep_hours', 7),
        "dietary_intake": getattr(latest_progress, 'calories_consumed', 2500),
        
        # Training and recovery data
        # ✅ يتم جلبها الآن من حقل metrics إذا لم تكن موجودة كأعمدة مستقلة
        "training_days_per_week": latest_workout.metrics.get('training_days_per_week', 3) if latest_workout and latest_workout.metrics else 3,
        "recovery_days_per_week": latest_workout.metrics.get('recovery_days_per_week', 2) if latest_workout and latest_workout.metrics else 2,
        
        # Biometric data
        "Heart_Rate_(HR)": getattr(latest_workout, 'avg_heart_rate', 0), # Corrected here
        "Muscle_Tension_(MT)": latest_workout.metrics.get('Muscle_Tension_(MT)', 0.5) if latest_workout and latest_workout.metrics else 0.5,
        "Body_Temperature_(BT)": latest_workout.metrics.get('Body_Temperature_(BT)', 36.5) if latest_workout and latest_workout.metrics else 36.5,
        "Breathing_Rate_(BR)": latest_workout.metrics.get('Breathing_Rate_(BR)', 16) if latest_workout and latest_workout.metrics else 16,
        "Blood_Pressure_Systolic_(BP)": latest_workout.metrics.get('Blood_Pressure_Systolic_(BP)', 120) if latest_workout and latest_workout.metrics else 120,
        "Blood_Pressure_Diastolic_(BP)": latest_workout.metrics.get('Blood_Pressure_Diastolic_(BP)', 80) if latest_workout and latest_workout.metrics else 80,
        
        # Other features
        "Training_Duration_(TD)": getattr(latest_workout, 'actual_duration', 60),
        "Wavelet_Features_(WF)": getattr(latest_readiness, 'wavelet_features', 0.5),
        "Feature_Weights_(FW)": getattr(latest_readiness, 'feature_weights', 0.9),
        
        # Categorical features
        "Training_Intensity_(TI)": getattr(latest_workout, 'difficulty_level', "Medium"), # يستخدم difficulty_level
        "Training_Type_(TT)": getattr(latest_workout, 'workout_type', "Cardio"),
        "Time_Interval_(TI)": latest_workout.metrics.get('Time_Interval_(TI)', "Morning") if latest_workout and latest_workout.metrics else "Morning",
        "Phase_of_Training_(PT)": getattr(latest_readiness, 'training_phase', "Build")
    }

    return input_data

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

            # ✅ قراءة أحدث سجل جاهزية من قاعدة البيانات
            latest_readiness = ReadinessScore.query.filter_by(
                athlete_id=user.id
            ).order_by(desc(ReadinessScore.date)).first()
            
            has_activity = db.session.query(WorkoutLog.id).filter_by(athlete_id=user.id).first()
            
            if not has_activity:
                readiness_score = None
                injury_risk = "No Data"
            elif latest_readiness:
                # ✅ إذا كان هناك سجل، استخدمه مباشرة
                readiness_score = latest_readiness.score
                injury_risk = latest_readiness.injury_risk
            else:
                readiness_score = None
                injury_risk = "No Data" # Show No Data if last update is old and no new activity

            
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

            profile_image_url = url_for('static', filename='uploads/' + (user.profile_image or 'default.jpeg'))

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
        # ✅ تسجيل الخطأ التفصيلي
        print(f"FATAL ERROR in get_coach_athletes: {traceback.format_exc()}")
        return jsonify({"msg": f"An error occurred: {str(e)}"}), 500

# ================================
# MANUAL ML DATA INPUT & PREDICTION ROUTE
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/predict-manual", methods=["POST"])
@jwt_required()
def run_manual_prediction(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # 1. Check relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    input_data = request.get_json()

    if not input_data:
        return jsonify({"error": "No input data provided"}), 400

    try:
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

        # 3. Store new records in WorkoutLog and AthleteProgress
        
        # A. WorkoutLog - ✅ تم تصحيح أسماء الحقول لتتناسب مع نموذج قاعدة البيانات
        new_workout_log = WorkoutLog(
            athlete_id=athlete_id,
            logged_at=datetime.utcnow(),
            date=datetime.utcnow().date(),
            title="Manual ML Input Session",
            
            avg_heart_rate=safe_int("heart_rate", 0), 
            difficulty_level=input_data.get("Training_Intensity_(TI)"),
            
            workout_type=input_data.get("Training_Type_(TT)"),
            planned_duration=safe_float("Training_Duration_(TD)", 60.0),
            actual_duration=safe_float("Training_Duration_(TD)", 60.0),
            total_time=safe_int("Training_Duration_(TD)", 60), # إضافة total_time
            session_type="workout",
            completion_status="completed",
            
            calories_burned=safe_int("dietary_intake", 0),
            
            # ✅ تخزين البيانات التي لا توجد في الأعمدة الرئيسية في حقل metrics كـ JSONB
            metrics={
                "Muscle_Tension_(MT)": safe_float("Muscle_Tension_(MT)", 0.0),
                "Body_Temperature_(BT)": safe_float("Body_Temperature_(BT)", 36.5),
                "Breathing_Rate_(BR)": safe_float("Breathing_Rate_(BR)", 16.0),
                "Time_Interval_(TI)": input_data.get("Time_Interval_(TI)"),
                "training_days_per_week": safe_int("training_days_per_week", 3),
                "recovery_days_per_week": safe_int("recovery_days_per_week", 2),
                
                "Blood_Pressure_Systolic_(BP)": safe_int("Blood_Pressure_Systolic_(BP)", 120),
                "Blood_Pressure_Diastolic_(BP)": safe_int("Blood_Pressure_Diastolic_(BP)", 80),
                "calories_consumed": safe_int("dietary_intake", 2500), # السعرات
            }
        )
        db.session.add(new_workout_log)

        # B. AthleteProgress - ✅ تم إزالة جميع الحقول المسببة للخطأ
        new_athlete_progress = AthleteProgress(
            athlete_id=athlete_id,
            date=datetime.utcnow().date(),
            
            # ✅ تم إضافة حقل calories_burned لضمان سلامة الـ Progress
            calories_burned=safe_float("dietary_intake", 0),
        )
        db.session.add(new_athlete_progress)
        
        # 4. Run ML service with the complete input_data
        result = predict_all(input_data)

        # 5. Store in MLInsight
        insight = MLInsight(
            athlete_id=athlete_id,
            generated_at=datetime.utcnow(),
            insight_data=result
        )
        db.session.add(insight)

        # 6. Store Readiness Score
        readiness_score = result.get("readiness_score")
        if readiness_score is not None:
            # ✅ تحويل القيمة إلى عدد صحيح آمن قبل الحفظ
            safe_readiness_score = safe_int("readiness_score", 0) 
            
            rs = ReadinessScore(
                athlete_id=athlete_id,
                date=datetime.utcnow().date(),
                score=safe_readiness_score, 
                injury_risk=str(result.get("injury_severity_prediction")),
                recovery_prediction=str(result.get("recovery_success_prediction"))
            )
            db.session.add(rs)

        db.session.commit()
        # ✅ بعد الـ commit بنجاح، يتم إرجاع النتيجة
        return jsonify({
            "message": "Prediction generated, and records updated successfully.",
            "readiness_score": result.get("readiness_score"),
            "injury_risk": result.get("injury_severity_prediction")
        }), 201

    except Exception as e:
        db.session.rollback()
        # ✅ تسجيل الخطأ بالتفصيل في نافذة الخادم
        print("--- FATAL MANUAL PREDICTION ERROR ---")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Details: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        print("-------------------------------------")

        return jsonify({"error": "An internal error occurred during prediction and storage. Please check server logs and input types."}), 500

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
    
    profile_image_url = url_for('static', filename='uploads/' + (athlete.profile_image or 'default.jpeg'))

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
        "compliance": compliance,
        "total_workouts": total_workouts,
        "completed_workouts": completed_workouts,
        "last_activity": last_activity,
        "recent_activities": recent_activities,
        # يتم عرض No Data إذا كانت البيانات فارغة
        "ml_insights": {
            "injury_severity": ml_data.get("injury_severity_prediction") if ml_data else "No Data",
            "recovery_success": ml_data.get("recovery_success_prediction") if ml_data else "No Data",
            "performance_class": ml_data.get("performance_class") if ml_data else "No Data",
            "periodization_recommendation": ml_data.get("periodization_recommendation") if ml_data else "No Data",
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
# Delete/Remove Athlete (FINAL)
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
            details={
                "athlete_id": athlete_id,
                "athlete_name": athlete.name if athlete else "Unknown",
                "action_type": "unassign",
                "reason": "Coach removed athlete from roster"
            },
            created_at=datetime.utcnow()
        )
        db.session.add(activity)

        db.session.commit()
        return jsonify({
            "msg": "Athlete unassigned successfully. Admin can reassign to another coach.",
            "status": "unassigned"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error unassigning athlete: {str(e)}"}), 500

# ================================
# Get Athlete Progress with ML Data
# ================================

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
        
        risk_map = {"low": 1, "medium": 2, "high": 3}
        injury_risks.append(risk_map.get(r.injury_risk, 0) if r else 0)

    return jsonify({
        "dates": dates,
        "weights": weights,
        "workouts": workouts,
        "readiness_scores": readiness_scores,
        "injury_risks": injury_risks
    })

# ================================
# Get Athlete Statistics (FINAL)
# ================================

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
            func.sum(
                db.case(
                    (WorkoutLog.completion_status == 'completed', 1),
                    else_=0
                )
            ).label('completed'),
            func.sum(WorkoutLog.calories_burned).label('total_calories'),
            func.sum(WorkoutLog.actual_duration).label('total_duration')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= start_date.date()
        ).first()

        latest_progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id
        ).order_by(desc(AthleteProgress.date)).first()

        latest_ml = MLInsight.query.filter_by(
            athlete_id=athlete_id
        ).order_by(desc(MLInsight.generated_at)).first()

        ml_data = latest_ml.insight_data if latest_ml else {}

        latest_readiness = ReadinessScore.query.filter_by(
            athlete_id=athlete_id
        ).order_by(desc(ReadinessScore.date)).first()

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
                "injury_severity": ml_data.get("injury_severity_prediction"),
                "recovery_success": ml_data.get("recovery_success_prediction"),
                "performance_class": ml_data.get("performance_class"),
                "periodization_recommendation": ml_data.get("periodization_recommendation"),
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
# Helper Functions
# ================================

def get_recent_activities(athlete_id, limit=5):
    """Get recent activities for an athlete"""
    activities = []

    recent_workouts = WorkoutLog.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(WorkoutLog.logged_at)).limit(limit).all()

    for workout in recent_workouts:
        time_ago = format_time_ago(workout.logged_at)
        activities.append({
            "icon": "bi-check-circle",
            "description": f"Completed workout: {workout.title or 'Training Session'}",
            "timestamp": time_ago
        })

    return activities

def format_time_ago(dt):
    """Format datetime as 'time ago' string"""
    if not dt:
        return "Unknown"

    time_diff = datetime.utcnow() - dt

    if time_diff.days == 0:
        if time_diff.seconds < 3600:
            return f"{time_diff.seconds // 60} minutes ago"
        else:
            return f"{time_diff.seconds // 3600} hours ago"
    elif time_diff.days == 1:
        return "Yesterday"
    elif time_diff.days < 7:
        return f"{time_diff.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")

# ================================
# Add existing routes (unchanged)
# ================================

@coach_bp.route("/athlete/<int:athlete_id>", methods=["GET"])
@jwt_required()
def get_athlete(athlete_id):
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

    return jsonify({
        "id": athlete.id,
        "name": athlete.name,
        "email": athlete.email,
        "age": profile.age if profile else None,
        "gender": profile.gender if profile else None,
        "weight": profile.weight if profile else None,
        "height": profile.height if profile else None,
        "team": profile.team if profile else None,
        "position": profile.position if profile else None
    })

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

        return jsonify({
            "msg": "Athlete added successfully",
            "athlete_id": new_athlete.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error adding athlete: {str(e)}"}), 500

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

    try:
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

        if not profile:
            profile = AthleteProfile(user_id=athlete_id)
            db.session.add(profile)

        if data.get("age") is not None:
            profile.age = data.get("age")
        if data.get("gender"):
            profile.gender = data.get("gender")
        if data.get("weight") is not None:
            profile.weight = data.get("weight")
        if data.get("height") is not None:
            profile.height = data.get("height")
        if data.get("team"):
            profile.team = data.get("team")
        if data.get("position"):
            profile.position = data.get("position")

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
        return jsonify({"msg": f"Error updating athlete: {str(e)}"}), 500

@coach_bp.route("/athlete/<int:athlete_id>/workouts", methods=["GET"])
@jwt_required()
def get_athlete_workouts(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()

    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    workouts = WorkoutLog.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(WorkoutLog.logged_at)).limit(10).all()

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

    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id
    ).first()

    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    plans = db.session.query(TrainingPlan).join(
        AthletePlan, AthletePlan.plan_id == TrainingPlan.id
    ).filter(
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
