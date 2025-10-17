from flask import request, jsonify, render_template, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.athlete_progress import AthleteProgress 
from app.models.athlete_goals import AthleteGoal
from app.models.training_plan import TrainingPlan
from app.models import WorkoutLog, User
from datetime import datetime, timedelta
from sqlalchemy import func
from . import athlete_bp

# ============================================================
# UTILITY FUNCTION (New)
# ============================================================
MAX_CALORIES_PER_WORKOUT = 1200 # الحد الأقصى المنطقي للسعرات الحرارية في الجلسة الواحدة

def get_clean_workouts_query(athlete_id, start_date=None):
    """
    تقوم بإنشاء استعلام أساسي لجلب التمارين المكتملة وتصفية القيم المتطرفة.
    """
    query = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.completion_status == 'completed',
        WorkoutLog.calories_burned <= MAX_CALORIES_PER_WORKOUT # التصفية هنا
    )
    if start_date:
        query = query.filter(WorkoutLog.date >= start_date.date())
        
    return query

# ============================================================
# VIEW: Progress Page
# ============================================================
@athlete_bp.route("/progress", methods=["GET"])
@jwt_required(optional=True)
def progress():
    """صفحة التقدم - لا تحتاج redirect للـ login"""
    return render_template("athlete/progress.html")


# ============================================================
# API: Get Progress Data
# ============================================================
@athlete_bp.route("/api/progress", methods=["GET"])
@jwt_required()
def get_progress():
    """
    جلب بيانات التقدم - محسّن للسرعة
    """
    try:
        athlete_id = int(get_jwt_identity())
        
        # Get period
        period = request.args.get('period', 'week')
        period_map = {'week': 7, 'month': 30, '3months': 90}
        days = period_map.get(period, 7)
        start_date = datetime.now() - timedelta(days=days)
        
        # Fetch records
        records = db.session.query(AthleteProgress).filter(
            AthleteProgress.athlete_id == athlete_id,
            AthleteProgress.date >= start_date.date()
        ).order_by(AthleteProgress.date.asc()).all()
        
        # Get latest record
        latest = db.session.query(AthleteProgress).filter(
            AthleteProgress.athlete_id == athlete_id
        ).order_by(AthleteProgress.date.desc()).first()
        
        if not latest:
            return jsonify({
                "records": [],
                "current_metrics": {
                    "health_score": 0,
                    "completed_goals": 0,
                    "total_goals": 0,
                    "avg_goal_progress": 0,
                    "weight": 0,
                    "weight_goal": 65,
                    "bmi": 0,
                    "body_fat": 0,
                    "muscle_mass": 0,
                    "consistency_score": 0
                }
            })
        
        # Convert records to JSON
        records_data = [{
            "id": p.id,
            "date": p.date.isoformat(),
            "weight": float(p.weight or 0),
            "weight_goal": float(p.weight_goal or 65),
            "calories": int(p.calories_burned or 0),
            "workouts": int(p.workouts_done or 0),
            "heart_rate": int(p.heart_rate or 0),
            "bmi": float(p.bmi or 0),
            "body_fat": float(p.body_fat or 0),
            "muscle_mass": float(p.muscle_mass or 0),
            "overall_health_score": float(p.overall_health_score or 0)
        } for p in records]
        
        current_metrics = {
            "workout_score": float(latest.workout_score or 0),
            "goals_completion_rate": float(latest.goals_completion_rate or 0),
            "completed_goals": int(latest.completed_goals or 0),
            "total_goals": int(latest.total_goals or 0),
            "avg_goal_progress": float(latest.avg_goal_progress or 0),
            "plan_adherence": float(latest.plan_adherence or 0),
            "consistency_score": float(latest.consistency_score or 0),
            "health_score": float(latest.overall_health_score or 0),
            "weight": float(latest.weight or 0),
            "weight_goal": float(latest.weight_goal or 65),
            "bmi": float(latest.bmi or 0),
            "body_fat": float(latest.body_fat or 0),
            "muscle_mass": float(latest.muscle_mass or 0)
        }
        
        return jsonify({
            "records": records_data,
            "current_metrics": current_metrics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting progress: {e}")
        return jsonify({"msg": f"Error: {str(e)}"}), 500


# ============================================================
# CALCULATION FUNCTIONS (FIXED LOGIC)
# ============================================================
def calculate_workout_score_optimized(athlete_id, period_days=7):
    """حساب محسّن لنقاط التمرين - يعتمد على التمارين النظيفة"""
    try:
        start_date = datetime.now() - timedelta(days=period_days)
        
        # *** التعديل: استخدام الاستعلام النظيف ***
        base_query = get_clean_workouts_query(athlete_id, start_date)
        
        workout_stats = db.session.query(
            func.count(WorkoutLog.id).label('total_workouts'),
            func.sum(WorkoutLog.actual_duration).label('total_duration'),
            func.sum(WorkoutLog.calories_burned).label('total_calories')
        ).filter(
            base_query.whereclause
        ).first()

        total_workouts = workout_stats.total_workouts or 0
        total_duration = workout_stats.total_duration or 0.1
        total_calories = workout_stats.total_calories or 0
        
        if total_workouts == 0:
            return 0
        
        # 1. نقاط المدة (Duration Score): أقصى حد 20 نقطة
        avg_duration_per_workout = (total_duration / total_workouts)
        duration_score = min(avg_duration_per_workout / 40 * 20, 20)
        
        # 2. نقاط السعرات/الشدة (Calorie/Intensity Score): أقصى حد 15 نقطة
        avg_cal_per_min = total_calories / total_duration if total_duration > 0 else 0
        calorie_score = min(avg_cal_per_min / 10 * 15, 15)
        
        # 3. مكافأة الإنجاز (Completion Bonus): أقصى حد 30 نقطة
        consistency_bonus = min(total_workouts / (period_days * 0.5) * 30, 30)
        
        total_score = duration_score + calorie_score + consistency_bonus
        return min(round(total_score, 1), 100)
        
    except Exception as e:
        current_app.logger.error(f"Error calculating workout score: {e}")
        return 0


def calculate_goals_completion_optimized(athlete_id):
    """حساب محسّن لإنجاز الأهداف"""
    try:
        goals = db.session.query(
            AthleteGoal.current_value,
            AthleteGoal.target_value
        ).filter(
            AthleteGoal.athlete_id == athlete_id
        ).all()
        
        if not goals:
            return 0, 0, 0, 0
        
        completed_count = 0
        total_progress = 0
        
        for current, target in goals:
            if target and target > 0:
                progress = min((current or 0) / target * 100, 100)
                total_progress += progress
                if progress >= 100:
                    completed_count += 1
        
        total_goals = len(goals)
        completion_rate = (completed_count / total_goals) * 100 if total_goals > 0 else 0
        avg_progress = total_progress / total_goals if total_goals > 0 else 0
        
        return completion_rate, completed_count, total_goals, avg_progress
        
    except Exception as e:
        current_app.logger.error(f"Error calculating goals: {e}")
        return 0, 0, 0, 0


def calculate_plan_adherence_optimized(athlete_id):
    """حساب محسّن للالتزام بالخطط"""
    try:
        active_plans = db.session.query(
            TrainingPlan.id,
            TrainingPlan.start_date,
            TrainingPlan.end_date
        ).filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingPlan.status == 'active'
        ).all()
        
        if not active_plans:
            return 0
        
        total_adherence = 0
        
        for plan_id, start_date, end_date in active_plans:
            if not start_date or not end_date:
                continue
                
            total_days = (end_date - start_date).days
            elapsed_days = (datetime.now().date() - start_date).days
            
            if total_days <= 0:
                continue
            
            expected_progress = min((elapsed_days / total_days) * 100, 100)
            
            # *** التعديل: استخدام الاستعلام النظيف لحساب التمارين المكتملة ضمن الخطة ***
            completed_workouts = get_clean_workouts_query(athlete_id, start_date).filter(
                WorkoutLog.date <= datetime.now().date()
            ).count() or 0
            
            expected_workouts = max((elapsed_days / 7) * 3.5, 1)
            actual_progress = min((completed_workouts / expected_workouts) * 100, 100)
            
            adherence = min((actual_progress / max(expected_progress, 1)) * 100, 100)
            total_adherence += adherence
        
        return total_adherence / len(active_plans) if active_plans else 0
        
    except Exception as e:
        current_app.logger.error(f"Error calculating plan adherence: {e}")
        return 0


def calculate_consistency_score_optimized(athlete_id, period_days=30):
    """حساب محسّن للاستمرارية - يعتمد على التمارين النظيفة"""
    try:
        start_date = datetime.now() - timedelta(days=period_days)
        
        # *** التعديل: استخدام الاستعلام النظيف ***
        workout_days = db.session.query(
            func.count(func.distinct(WorkoutLog.date))
        ).filter(
            get_clean_workouts_query(athlete_id, start_date).whereclause
        ).scalar() or 0
        
        consistency = (workout_days / period_days) * 100 
        return min(round(consistency, 1), 100)
        
    except Exception as e:
        current_app.logger.error(f"Error calculating consistency: {e}")
        return 0


# ============================================================
# NEW WEIGHTED PERFORMANCE SCORE MODEL
# ============================================================
def calculate_weighted_performance_score(consistency, avg_goal_progress, workout_score, plan_adherence):
    """
    نموذج القواعد المرجحة (Weighted Rule-Based Model) لحساب الأداء الكلي.
    """
    
    # الأوزان المحددة
    WEIGHTS = {
        'consistency': 0.40,
        'goal_progress': 0.30,
        'workout_quality': 0.20,
        'plan_adherence': 0.10
    }
    
    score_consistency = consistency
    score_goals = avg_goal_progress
    score_workout = workout_score
    score_adherence = plan_adherence
    
    # حساب النتيجة المرجحة
    weighted_score = (
        score_consistency * WEIGHTS['consistency'] +
        score_goals * WEIGHTS['goal_progress'] +
        score_workout * WEIGHTS['workout_quality'] +
        score_adherence * WEIGHTS['plan_adherence']
    )
    
    # النتيجة الكلية من 100
    return min(round(weighted_score, 1), 100)


def calculate_health_score_optimized(athlete_id):
    """
    هذه الدالة تبقى لحساب النقاط الصحية بناءً على بيانات الجسم فقط (BMI, Fat, HR)
    """
    try:
        latest = db.session.query(
            AthleteProgress.bmi,
            AthleteProgress.body_fat,
            AthleteProgress.heart_rate
        ).filter(
            AthleteProgress.athlete_id == athlete_id
        ).order_by(
            AthleteProgress.date.desc()
        ).first()
        
        health_score = 50
        
        if latest:
            bmi, body_fat, heart_rate = latest
            
            if bmi and 18.5 <= bmi <= 24.9:
                health_score += 20
            elif bmi and 25 <= bmi <= 29.9:
                health_score += 15
            elif bmi:
                health_score += 10
            
            if body_fat and body_fat < 25:
                health_score += 15
            elif body_fat and body_fat < 30:
                health_score += 10
            elif body_fat:
                health_score += 5
            
            if heart_rate and 60 <= heart_rate <= 100:
                health_score += 15
            elif heart_rate and 50 <= heart_rate <= 110:
                health_score += 10
            elif heart_rate:
                health_score += 5
        
        return min(round(health_score, 1), 100)
        
    except Exception as e:
        current_app.logger.error(f"Error calculating health score: {e}")
        return 50


def save_calculated_progress_optimized(athlete_id):
    """حفظ التقدم المحسوب"""
    try:
        # Calculate all required sub-metrics
        # استخدام الدوال المعدلة
        workout_score = calculate_workout_score_optimized(athlete_id) 
        goals_rate, completed_goals, total_goals, avg_goal_progress = calculate_goals_completion_optimized(athlete_id)
        plan_adherence = calculate_plan_adherence_optimized(athlete_id)
        consistency = calculate_consistency_score_optimized(athlete_id)
        health_score = calculate_health_score_optimized(athlete_id) # Health Score (based on body metrics)
        
        # Calculate the Final Weighted Performance Score (The Model)
        overall_performance_score = calculate_weighted_performance_score(
            consistency, avg_goal_progress, workout_score, plan_adherence
        )
        
        # Get last week data (NOTE: هذا الجزء يجب أن يستخدم البيانات الحقيقية لعرضها، وليس المصفاة)
        last_week = datetime.now() - timedelta(days=7)
        
        # ******************************************************************************
        # *** التعديل: جلب إجمالي السعرات والتمارين (غير المصفاة) للعرض في Quick Stats ***
        # ******************************************************************************
        workout_stats_display = db.session.query(
            func.count(WorkoutLog.id).label('workouts'),
            func.sum(WorkoutLog.calories_burned).label('calories')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= last_week.date(),
            WorkoutLog.completion_status == 'completed' 
        ).first()
        
        workouts_done = workout_stats_display.workouts or 0
        total_calories = workout_stats_display.calories or 0
        
        # Get latest health data
        latest_health = db.session.query(
            AthleteProgress.weight,
            AthleteProgress.weight_goal,
            AthleteProgress.heart_rate,
            AthleteProgress.bmi,
            AthleteProgress.body_fat,
            AthleteProgress.muscle_mass
        ).filter(
            AthleteProgress.athlete_id == athlete_id
        ).order_by(
            AthleteProgress.date.desc()
        ).first()
        
        # Create or update today's record
        today = datetime.now().date()
        progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id,
            date=today
        ).first()
        
        if not progress:
            progress = AthleteProgress(athlete_id=athlete_id, date=today)
            db.session.add(progress)
        
        # Update all fields
        if latest_health:
            progress.weight = latest_health.weight
            progress.weight_goal = latest_health.weight_goal or 65
            progress.heart_rate = latest_health.heart_rate
            progress.bmi = latest_health.bmi
            progress.body_fat = latest_health.body_fat
            progress.muscle_mass = latest_health.muscle_mass
        
        # *** ملاحظة: يتم حفظ البيانات الحقيقية (التي قد تكون مبالغ فيها) هنا لعرضها في Quick Stats ***
        progress.calories_burned = int(total_calories)
        progress.workouts_done = workouts_done
        
        # حفظ نتائج النموذج (Performance Score)
        progress.overall_health_score = overall_performance_score
        
        # حفظ المقاييس الفرعية
        progress.workout_score = workout_score
        progress.goals_completion_rate = goals_rate
        progress.plan_adherence = plan_adherence
        progress.consistency_score = consistency
        progress.completed_goals = completed_goals
        progress.total_goals = total_goals
        progress.avg_goal_progress = round(avg_goal_progress, 1)
        
        db.session.commit()
        
        return progress
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving progress: {e}")
        raise


# ============================================================
# API: Calculate Progress
# ============================================================
@athlete_bp.route("/api/calculate_progress", methods=["POST"])
@jwt_required()
def calculate_and_save_progress():
    """حساب وحفظ التقدم"""
    try:
        athlete_id = int(get_jwt_identity())
        
        # Calculate and save
        progress_record = save_calculated_progress_optimized(athlete_id)
        
        return jsonify({
            "success": True,
            "msg": "Progress calculated successfully",
            "progress": {
                "date": progress_record.date.isoformat(),
                "overall_health_score": float(progress_record.overall_health_score or 0)
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error calculating progress: {e}")
        return jsonify({
            "success": False,
            "msg": f"Error: {str(e)}"
        }), 400


# ============================================================
# API: Add Manual Progress
# ============================================================
@athlete_bp.route("/api/progress", methods=["POST"])
@jwt_required()
def add_progress():
    """إضافة تقدم يدوي"""
    try:
        athlete_id = int(get_jwt_identity())
        data = request.get_json()
        today = datetime.now().date()
        
        # Find existing record
        progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id,
            date=today
        ).first()
        
        if not progress:
            progress = AthleteProgress(athlete_id=athlete_id, date=today)
            db.session.add(progress)
        
        # Update data
        if 'weight' in data:
            progress.weight = float(data['weight'])
        if 'weight_goal' in data:
            progress.weight_goal = float(data['weight_goal'])
        if 'heart_rate' in data:
            progress.heart_rate = int(data['heart_rate'])
        if 'bmi' in data:
            progress.bmi = float(data['bmi'])
        if 'body_fat' in data:
            progress.body_fat = float(data['body_fat'])
        if 'muscle_mass' in data:
            progress.muscle_mass = float(data['muscle_mass'])
        
        db.session.commit()
        
        # Recalculate progress
        save_calculated_progress_optimized(athlete_id)
        
        return jsonify({
            "msg": "Progress added successfully",
            "id": progress.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding progress: {e}")
        return jsonify({"msg": f"Error: {str(e)}"}), 400


# ============================================================
# API: Delete Progress
# ============================================================
@athlete_bp.route("/api/progress/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_progress(id):
    """حذف سجل تقدم"""
    try:
        progress = AthleteProgress.query.get_or_404(id)
        
        if progress.athlete_id != int(get_jwt_identity()):
            return jsonify({"msg": "Unauthorized access"}), 403
        
        db.session.delete(progress)
        db.session.commit()
        
        return jsonify({"msg": "Progress deleted successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting progress: {e}")
        return jsonify({"msg": f"Error: {str(e)}"}), 400
