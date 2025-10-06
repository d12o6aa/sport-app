# app/routes/admin/dashboard.py

from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
# 🆕 Import 'case' from the main sqlalchemy module
from sqlalchemy import func, extract, and_, case
from datetime import datetime, timedelta, date
from app import db
from app.models import (
    User, WorkoutLog, CoachAthlete, TrainingPlan, 
    AthleteProgress, AdminProfile
)

from . import admin_bp

def is_admin(user_id):
    user = User.query.get(user_id)
    return user and user.role == "admin"

@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    identity = get_jwt_identity()
    if not is_admin(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # ==================== Basic User Stats ====================
    total_users = User.query.filter_by(is_deleted=False).count()
    active_users = User.query.filter_by(status='active', is_deleted=False).count()
    
    # Role distribution
    admins_count = User.query.filter_by(role='admin', is_deleted=False).count()
    coaches_count = User.query.filter_by(role='coach', is_deleted=False).count()
    athletes_count = User.query.filter_by(role='athlete', is_deleted=False).count()
    
    # Active percentage
    active_percentage = round((active_users / total_users * 100), 1) if total_users > 0 else 0
    
    # ==================== New Users This Month ====================
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)
    new_users_this_month = User.query.filter(
        User.created_at >= first_day_of_month,
        User.is_deleted == False
    ).count()
    
    # ==================== Unassigned Athletes ====================
    unassigned_athletes = User.query.filter(
        User.role == 'athlete',
        User.is_deleted == False,
        ~User.coach_links.any()
    ).count()
    
    # ==================== Workout Stats ====================
    # Total workouts
    total_workouts = WorkoutLog.query.count()
    
    # Workouts today
    workouts_today = WorkoutLog.query.filter(
        WorkoutLog.date == today
    ).count()
    
    # Completed workouts
    completed_workouts = WorkoutLog.query.filter_by(
        completion_status='completed'
    ).count()
    
    # Completion rate
    completion_rate = round((completed_workouts / total_workouts * 100), 1) if total_workouts > 0 else 0
    
    # ==================== Active Training Plans ====================
    active_plans = TrainingPlan.query.filter_by(status='active').count()
    
    # ==================== Recent Users (Last 10) ====================
    recent_users = User.query.filter_by(is_deleted=False)\
        .order_by(User.created_at.desc())\
        .limit(10)\
        .all()
    
    # ==================== Top Performing Athletes ====================
    # 🆕 CORRECTED: Use case() imported from sqlalchemy, not func.case()
    top_athletes = db.session.query(
        User,
        func.count(WorkoutLog.id).label('workout_count'),
        func.avg(
            case(
                (WorkoutLog.completion_status == 'completed', 100),
                else_=0
            )
        ).label('completion_rate')
    ).join(WorkoutLog, User.id == WorkoutLog.athlete_id)\
     .filter(User.role == 'athlete', User.is_deleted == False)\
     .group_by(User.id)\
     .order_by(func.count(WorkoutLog.id).desc())\
     .limit(10)\
     .all()
    
    # Format top athletes data
    top_athletes_data = [
        {
            'user': athlete,
            'workout_count': workout_count,
            'completion_rate': round(completion_rate, 1) if completion_rate else 0
        }
        for athlete, workout_count, completion_rate in top_athletes
    ]
    
    # ==================== User Growth (Last 6 Months) ====================
    six_months_ago = datetime.now() - timedelta(days=180)
    
    # Get monthly user counts
    monthly_growth = db.session.query(
        extract('year', User.created_at).label('year'),
        extract('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= six_months_ago,
        User.is_deleted == False
    ).group_by('year', 'month')\
     .order_by('year', 'month')\
     .all()
    
    # Format growth data for Chart.js
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    growth_labels = []
    growth_data = []
    cumulative_count = User.query.filter(
        User.created_at < six_months_ago,
        User.is_deleted == False
    ).count()
    
    for year, month, count in monthly_growth:
        growth_labels.append(f"{month_names[int(month)-1]} {int(year)}")
        cumulative_count += count
        growth_data.append(cumulative_count)
    
    # If no data, create empty arrays
    if not growth_labels:
        growth_labels = [month_names[datetime.now().month - 1]]
        growth_data = [total_users]
    
    return render_template(
        "dashboard/admin_dashboard.html",
        # Basic stats
        total_users=total_users,
        active_users=active_users,
        active_percentage=active_percentage,
        new_users_this_month=new_users_this_month,
        
        # Role distribution
        admins_count=admins_count,
        coaches_count=coaches_count,
        athletes_count=athletes_count,
        
        # Athlete stats
        unassigned_athletes=unassigned_athletes,
        
        # Workout stats
        workouts_today=workouts_today,
        total_workouts=total_workouts,
        completed_workouts=completed_workouts,
        completion_rate=completion_rate,
        
        # Plans
        active_plans=active_plans,
        
        # Lists
        recent_users=recent_users,
        top_athletes=top_athletes_data,
        
        # Chart data
        growth_labels=growth_labels,
        growth_data=growth_data
    )
    
