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
# CONSTANTS & UTILITY
# ============================================================
MAX_CALORIES_PER_WORKOUT = 1200

def get_clean_workouts_query(athlete_id, start_date=None):
    """استعلام للتمارين المكتملة مع تصفية القيم الشاذة"""
    query = WorkoutLog.query.filter(
        WorkoutLog.athlete_id == athlete_id,
        WorkoutLog.completion_status == 'completed',
        WorkoutLog.calories_burned <= MAX_CALORIES_PER_WORKOUT
    )
    if start_date:
        query = query.filter(WorkoutLog.date >= start_date.date())
    return query

# ============================================================
# REALISTIC CALCULATION FUNCTIONS
# ============================================================

def calculate_consistency_realistic(athlete_id, period_days=30):
    """حساب الاستمرارية: الهدف 4 أيام/أسبوع"""
    try:
        start_date = datetime.now() - timedelta(days=period_days)
        
        workout_days = db.session.query(
            func.count(func.distinct(WorkoutLog.date))
        ).filter(
            get_clean_workouts_query(athlete_id, start_date).whereclause
        ).scalar() or 0
        
        ideal_days_per_week = 4
        weeks = period_days / 7
        ideal_total_days = ideal_days_per_week * weeks
        
        ratio = workout_days / ideal_total_days if ideal_total_days > 0 else 0
        
        if ratio >= 1.0:
            score = 100
        elif ratio >= 0.85:
            score = 90 + (ratio - 0.85) * 66.67
        elif ratio >= 0.70:
            score = 80 + (ratio - 0.70) * 66.67
        elif ratio >= 0.50:
            score = 65 + (ratio - 0.50) * 75
        elif ratio >= 0.30:
            score = 40 + (ratio - 0.30) * 125
        else:
            score = ratio * 133.33
        
        return min(round(score, 1), 100)
    except Exception as e:
        current_app.logger.error(f"Error calculating consistency: {e}")
        return 0


def calculate_workout_quality_realistic(athlete_id, period_days=7):
    """تقييم جودة التمارين: المدة + الشدة + التنوع"""
    try:
        start_date = datetime.now() - timedelta(days=period_days)
        base_query = get_clean_workouts_query(athlete_id, start_date)
        
        stats = db.session.query(
            func.count(WorkoutLog.id).label('total'),
            func.sum(WorkoutLog.actual_duration).label('duration'),
            func.sum(WorkoutLog.calories_burned).label('calories'),
            func.count(func.distinct(WorkoutLog.workout_type)).label('types')
        ).filter(base_query.whereclause).first()

        total = stats.total or 0
        duration = stats.duration or 0
        calories = stats.calories or 0
        types = stats.types or 1
        
        if total == 0:
            return 0
        
        # 1. Duration Score (0-35)
        avg_duration = duration / total
        if 45 <= avg_duration <= 60:
            duration_score = 35
        elif 30 <= avg_duration < 45:
            duration_score = 25 + ((avg_duration - 30) / 15) * 10
        elif 60 < avg_duration <= 90:
            duration_score = 30
        elif 20 <= avg_duration < 30:
            duration_score = 15 + ((avg_duration - 20) / 10) * 10
        else:
            duration_score = min(avg_duration * 0.5, 15)
        
        # 2. Intensity Score (0-40)
        cal_per_min = calories / duration if duration > 0 else 0
        if 6 <= cal_per_min <= 10:
            intensity_score = 40
        elif 4 <= cal_per_min < 6:
            intensity_score = 25 + ((cal_per_min - 4) / 2) * 15
        elif 10 < cal_per_min <= 15:
            intensity_score = 35
        elif 2 <= cal_per_min < 4:
            intensity_score = 10 + ((cal_per_min - 2) / 2) * 15
        else:
            intensity_score = min(cal_per_min * 2, 10)
        
        # 3. Variety Score (0-25)
        variety_score = {4: 25, 3: 20, 2: 12}.get(types, 5)
        
        return min(round(duration_score + intensity_score + variety_score, 1), 100)
    except Exception as e:
        current_app.logger.error(f"Error calculating quality: {e}")
        return 0


def calculate_improvement_realistic(athlete_id):
    """قياس التحسن: مقارنة آخر 7 أيام بالـ 7 السابقة"""
    try:
        now = datetime.now()
        current_start = now - timedelta(days=7)
        prev_start = now - timedelta(days=14)
        
        current = db.session.query(
            func.count(WorkoutLog.id).label('count'),
            func.sum(WorkoutLog.calories_burned).label('cals'),
            func.sum(WorkoutLog.actual_duration).label('dur')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= current_start.date(),
            WorkoutLog.date < now.date(),
            WorkoutLog.completion_status == 'completed',
            WorkoutLog.calories_burned <= MAX_CALORIES_PER_WORKOUT
        ).first()
        
        previous = db.session.query(
            func.count(WorkoutLog.id).label('count'),
            func.sum(WorkoutLog.calories_burned).label('cals'),
            func.sum(WorkoutLog.actual_duration).label('dur')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= prev_start.date(),
            WorkoutLog.date < current_start.date(),
            WorkoutLog.completion_status == 'completed',
            WorkoutLog.calories_burned <= MAX_CALORIES_PER_WORKOUT
        ).first()
        
        curr_count = current.count or 0
        prev_count = previous.count or 0
        
        if prev_count == 0 and curr_count > 0:
            return 70
        if curr_count == 0:
            return 0
        if prev_count == 0:
            return 50
        
        curr_avg = (current.cals or 0) / curr_count
        prev_avg = (previous.cals or 0) / prev_count
        
        improvement = ((curr_avg - prev_avg) / prev_avg) * 100 if prev_avg > 0 else 0
        
        score = 50 + improvement
        return min(max(round(score, 1), 0), 100)
    except Exception as e:
        current_app.logger.error(f"Error calculating improvement: {e}")
        return 50


def calculate_goal_achievement_realistic(athlete_id):
    """تقييم الأهداف مع أوزان حسب الموعد النهائي"""
    try:
        goals = db.session.query(
            AthleteGoal.current_value,
            AthleteGoal.target_value,
            AthleteGoal.due_date
        ).filter(AthleteGoal.athlete_id == athlete_id).all()
        
        if not goals:
            return 0
        
        total_score = 0
        weight_sum = 0
        
        for current, target, due_date in goals:
            if not target or target <= 0:
                continue
            
            progress = min((current or 0) / target * 100, 100)
            weight = 1.0
            
            if due_date:
                days_left = (due_date - datetime.now().date()).days
                if days_left < 0:
                    weight = 0.5
                elif days_left <= 7:
                    weight = 1.5
                elif days_left <= 30:
                    weight = 1.2
            
            total_score += progress * weight
            weight_sum += weight
        
        return min(round(total_score / weight_sum if weight_sum > 0 else 0, 1), 100)
    except Exception as e:
        current_app.logger.error(f"Error calculating goals: {e}")
        return 0


def calculate_plan_adherence_realistic(athlete_id):
    """تقييم الالتزام بالخطط"""
    try:
        plans = db.session.query(
            TrainingPlan.start_date,
            TrainingPlan.end_date,
            TrainingPlan.sessions_per_week
        ).filter(
            TrainingPlan.athlete_id == athlete_id,
            TrainingPlan.status == 'active'
        ).all()
        
        if not plans:
            return 50
        
        total_adherence = 0
        
        for start, end, sessions in plans:
            if not start or not end:
                continue
            
            elapsed = (datetime.now().date() - start).days
            total = (end - start).days
            
            if total <= 0 or elapsed < 0:
                continue
            
            weeks = elapsed / 7
            expected = weeks * (sessions or 3)
            
            actual = get_clean_workouts_query(athlete_id, start).filter(
                WorkoutLog.date <= datetime.now().date()
            ).count() or 0
            
            if expected > 0:
                adherence = min((actual / expected) * 100, 120)
                
                if adherence >= 100:
                    score = 100
                elif adherence >= 80:
                    score = 80 + (adherence - 80)
                elif adherence >= 60:
                    score = 60 + (adherence - 60)
                else:
                    score = adherence
                
                total_adherence += score
        
        return round(total_adherence / len(plans), 1) if plans else 50
    except Exception as e:
        current_app.logger.error(f"Error calculating adherence: {e}")
        return 50


def calculate_weighted_performance(consistency, improvement, goals, quality, adherence):
    """النموذج المرجح النهائي"""
    WEIGHTS = {
        'consistency': 0.30,
        'quality': 0.25,
        'goals': 0.20,
        'improvement': 0.15,
        'adherence': 0.10
    }
    
    score = (
        consistency * WEIGHTS['consistency'] +
        quality * WEIGHTS['quality'] +
        goals * WEIGHTS['goals'] +
        improvement * WEIGHTS['improvement'] +
        adherence * WEIGHTS['adherence']
    )
    
    return min(round(score, 1), 100)


# ============================================================
# SAVE PROGRESS
# ============================================================

def save_calculated_progress_optimized(athlete_id):
    """حساب وحفظ التقدم"""
    try:
        consistency = calculate_consistency_realistic(athlete_id, 30)
        quality = calculate_workout_quality_realistic(athlete_id, 7)
        improvement = calculate_improvement_realistic(athlete_id)
        goals = calculate_goal_achievement_realistic(athlete_id)
        adherence = calculate_plan_adherence_realistic(athlete_id)
        
        overall = calculate_weighted_performance(
            consistency, improvement, goals, quality, adherence
        )
        
        # بيانات آخر أسبوع (للعرض فقط - غير مصفاة)
        last_week = datetime.now() - timedelta(days=7)
        stats = db.session.query(
            func.count(WorkoutLog.id).label('workouts'),
            func.sum(WorkoutLog.calories_burned).label('calories')
        ).filter(
            WorkoutLog.athlete_id == athlete_id,
            WorkoutLog.date >= last_week.date(),
            WorkoutLog.completion_status == 'completed'
        ).first()
        
        workouts_done = stats.workouts or 0
        total_calories = stats.calories or 0
        
        # بيانات صحية
        health = db.session.query(
            AthleteProgress.weight,
            AthleteProgress.weight_goal,
            AthleteProgress.heart_rate,
            AthleteProgress.bmi,
            AthleteProgress.body_fat,
            AthleteProgress.muscle_mass
        ).filter(
            AthleteProgress.athlete_id == athlete_id
        ).order_by(AthleteProgress.date.desc()).first()
        
        # حفظ السجل
        today = datetime.now().date()
        progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id, date=today
        ).first()
        
        if not progress:
            progress = AthleteProgress(athlete_id=athlete_id, date=today)
            db.session.add(progress)
        
        if health:
            progress.weight = health.weight
            progress.weight_goal = health.weight_goal or 65
            progress.heart_rate = health.heart_rate
            progress.bmi = health.bmi
            progress.body_fat = health.body_fat
            progress.muscle_mass = health.muscle_mass
        
        progress.calories_burned = int(total_calories)
        progress.workouts_done = workouts_done
        progress.overall_health_score = overall
        progress.workout_score = quality
        progress.consistency_score = consistency
        progress.plan_adherence = adherence
        
        # أهداف
        goal_stats = calculate_goals_completion_optimized(athlete_id)
        progress.goals_completion_rate = goal_stats[0]
        progress.completed_goals = goal_stats[1]
        progress.total_goals = goal_stats[2]
        progress.avg_goal_progress = round(goal_stats[3], 1)
        
        db.session.commit()
        return progress
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving progress: {e}")
        raise


def calculate_goals_completion_optimized(athlete_id):
    """حساب إحصائيات الأهداف"""
    try:
        goals = db.session.query(
            AthleteGoal.current_value,
            AthleteGoal.target_value
        ).filter(AthleteGoal.athlete_id == athlete_id).all()
        
        if not goals:
            return 0, 0, 0, 0
        
        completed = 0
        total_progress = 0
        
        for current, target in goals:
            if target and target > 0:
                progress = min((current or 0) / target * 100, 100)
                total_progress += progress
                if progress >= 100:
                    completed += 1
        
        total = len(goals)
        rate = (completed / total) * 100 if total > 0 else 0
        avg = total_progress / total if total > 0 else 0
        
        return rate, completed, total, avg
    except Exception as e:
        current_app.logger.error(f"Error calculating goals: {e}")
        return 0, 0, 0, 0


# ============================================================
# ROUTES
# ============================================================

@athlete_bp.route("/progress", methods=["GET"])
@jwt_required(optional=True)
def progress():
    return render_template("athlete/progress.html")


@athlete_bp.route("/api/progress", methods=["GET"])
@jwt_required()
def get_progress():
    try:
        athlete_id = int(get_jwt_identity())
        
        period = request.args.get('period', 'week')
        days = {'week': 7, 'month': 30, '3months': 90}.get(period, 7)
        start_date = datetime.now() - timedelta(days=days)
        
        records = db.session.query(AthleteProgress).filter(
            AthleteProgress.athlete_id == athlete_id,
            AthleteProgress.date >= start_date.date()
        ).order_by(AthleteProgress.date.asc()).all()
        
        latest = db.session.query(AthleteProgress).filter(
            AthleteProgress.athlete_id == athlete_id
        ).order_by(AthleteProgress.date.desc()).first()
        
        if not latest:
            return jsonify({"records": [], "current_metrics": {}})
        
        records_data = [{
            "id": p.id,
            "date": p.date.isoformat(),
            "weight": float(p.weight or 0),
            "calories": int(p.calories_burned or 0),
            "workouts": int(p.workouts_done or 0),
            "overall_health_score": float(p.overall_health_score or 0)
        } for p in records]
        
        current_metrics = {
            "workout_score": float(latest.workout_score or 0),
            "consistency_score": float(latest.consistency_score or 0),
            "plan_adherence": float(latest.plan_adherence or 0),
            "health_score": float(latest.overall_health_score or 0),
            "completed_goals": int(latest.completed_goals or 0),
            "total_goals": int(latest.total_goals or 0),
            "avg_goal_progress": float(latest.avg_goal_progress or 0)
        }
        
        return jsonify({"records": records_data, "current_metrics": current_metrics})
        
    except Exception as e:
        current_app.logger.error(f"Error getting progress: {e}")
        return jsonify({"msg": f"Error: {str(e)}"}), 500


@athlete_bp.route("/api/calculate_progress", methods=["POST"])
@jwt_required()
def calculate_and_save_progress():
    try:
        athlete_id = int(get_jwt_identity())
        progress = save_calculated_progress_optimized(athlete_id)
        
        return jsonify({
            "success": True,
            "msg": "Progress calculated",
            "progress": {
                "date": progress.date.isoformat(),
                "score": float(progress.overall_health_score or 0)
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": str(e)}), 400


@athlete_bp.route("/api/progress", methods=["POST"])
@jwt_required()
def add_progress():
    try:
        athlete_id = int(get_jwt_identity())
        data = request.get_json()
        today = datetime.now().date()
        
        progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id, date=today
        ).first()
        
        if not progress:
            progress = AthleteProgress(athlete_id=athlete_id, date=today)
            db.session.add(progress)
        
        for field in ['weight', 'weight_goal', 'heart_rate', 'bmi', 'body_fat', 'muscle_mass']:
            if field in data:
                setattr(progress, field, float(data[field]) if '.' in str(data[field]) else int(data[field]))
        
        db.session.commit()
        save_calculated_progress_optimized(athlete_id)
        
        return jsonify({"msg": "Progress added", "id": progress.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400


@athlete_bp.route("/api/progress/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_progress(id):
    try:
        progress = AthleteProgress.query.get_or_404(id)
        
        if progress.athlete_id != int(get_jwt_identity()):
            return jsonify({"msg": "Unauthorized"}), 403
        
        db.session.delete(progress)
        db.session.commit()
        
        return jsonify({"msg": "Deleted"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": str(e)}), 400