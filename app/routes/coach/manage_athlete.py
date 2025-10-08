# ================================
# Enhanced Coach Athlete Management Backend
# ================================

from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db
from app.models import (
    User, CoachAthlete, TrainingPlan, WorkoutLog, 
    ActivityLog, AthleteProgress, AthleteProfile, AthletePlan
)
from . import coach_bp

def is_coach(user_id):
    user = User.query.get(user_id)
    return user and user.role == "coach"

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
# Get All Athletes (Enhanced)
# ================================

@coach_bp.route("/athletes", methods=["GET"])
@jwt_required()
def get_coach_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    try:
        # Get athletes with comprehensive data
        athletes = db.session.query(
            User,
            AthleteProfile,
            func.max(WorkoutLog.logged_at).label('last_workout'),
            func.count(WorkoutLog.id).label('total_workouts'),
            func.sum(
                db.case(
                    (WorkoutLog.completion_status == 'completed', 1),
                    else_=0
                )
            ).label('completed_workouts')
        ).join(
            CoachAthlete, CoachAthlete.athlete_id == User.id
        ).outerjoin(
            AthleteProfile, AthleteProfile.user_id == User.id
        ).outerjoin(
            WorkoutLog, WorkoutLog.athlete_id == User.id
        ).filter(
            CoachAthlete.coach_id == identity,
            CoachAthlete.is_active == True,
            User.is_deleted == False
        ).group_by(
            User.id, AthleteProfile.user_id
        ).all()

        athlete_list = []
        for athlete_data in athletes:
            user = athlete_data[0]
            profile = athlete_data[1]
            last_workout = athlete_data[2]
            total_workouts = athlete_data[3] or 0
            completed_workouts = athlete_data[4] or 0
            
            # Calculate compliance
            compliance = 0
            if total_workouts > 0:
                compliance = round((completed_workouts / total_workouts) * 100, 1)
            
            # Format last activity
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
            
            athlete_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "last_activity": last_activity,
                "compliance": compliance,
                "total_workouts": total_workouts,
                "completed_workouts": completed_workouts
            })

        return jsonify(athlete_list)
    
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500

# ================================
# Get Single Athlete Details
# ================================

@coach_bp.route("/athlete/<int:athlete_id>", methods=["GET"])
@jwt_required()
def get_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify coach-athlete relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
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

# ================================
# Get Detailed Athlete Information
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/details", methods=["GET"])
@jwt_required()
def get_athlete_details(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()
    
    # Get workout stats
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
    
    # Get last activity
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
    
    # Get recent activities
    recent_activities = get_recent_activities(athlete_id)
    
    return jsonify({
        "id": athlete.id,
        "name": athlete.name,
        "email": athlete.email,
        "status": athlete.status,
        "profile_image": athlete.profile_image_url if hasattr(athlete, 'profile_image_url') else None,
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
        "recent_activities": recent_activities
    })

def get_recent_activities(athlete_id, limit=5):
    """Get recent activities for an athlete"""
    activities = []
    
    # Get recent workouts
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
# Get Athlete Progress Data
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_athlete_progress(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    # Get progress data for last 30 days
    start_date = datetime.utcnow() - timedelta(days=30)
    
    progress_data = AthleteProgress.query.filter(
        AthleteProgress.athlete_id == athlete_id,
        AthleteProgress.date >= start_date
    ).order_by(AthleteProgress.date).all()
    
    dates = []
    weights = []
    workouts = []
    
    for progress in progress_data:
        dates.append(progress.date.strftime("%b %d"))
        weights.append(float(progress.weight) if progress.weight else None)
        workouts.append(progress.workouts_done or 0)
    
    return jsonify({
        "dates": dates,
        "weights": weights,
        "workouts": workouts
    })

# ================================
# Get Athlete Workouts
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/workouts", methods=["GET"])
@jwt_required()
def get_athlete_workouts(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    workouts = WorkoutLog.query.filter_by(
        athlete_id=athlete_id
    ).order_by(desc(WorkoutLog.date)).limit(10).all()
    
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

# ================================
# Get Athlete Training Plans
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/plans", methods=["GET"])
@jwt_required()
def get_athlete_plans(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    # Get plans assigned to this athlete
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

# ================================
# Add New Athlete (Enhanced)
# ================================

@coach_bp.route("/athlete/add", methods=["POST"])
@jwt_required()
def add_athlete():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    
    # Validate required fields
    required_fields = ["name", "email", "password"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"msg": f"Missing required field: {field}"}), 400

    # Check if email already exists
    if User.query.filter_by(email=data.get("email")).first():
        return jsonify({"msg": "Email already registered"}), 400

    try:
        # Create new athlete user
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

        # Create athlete profile
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

        # Link athlete to coach
        link = CoachAthlete(
            coach_id=identity,
            athlete_id=new_athlete.id,
            assigned_at=datetime.utcnow(),
            status="approved",
            is_active=True
        )
        db.session.add(link)

        # Log activity
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

# ================================
# Update Athlete (Enhanced)
# ================================

@coach_bp.route("/athlete/<int:athlete_id>", methods=["PUT"])
@jwt_required()
def update_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.get_json()
    athlete = User.query.get_or_404(athlete_id)
    profile = AthleteProfile.query.filter_by(user_id=athlete_id).first()

    try:
        # Update user fields
        if data.get("name"):
            athlete.name = data.get("name")
        if data.get("email"):
            # Check if email is already taken by another user
            existing = User.query.filter(
                User.email == data.get("email"),
                User.id != athlete_id
            ).first()
            if existing:
                return jsonify({"msg": "Email already in use"}), 400
            athlete.email = data.get("email")

        # Create profile if doesn't exist
        if not profile:
            profile = AthleteProfile(user_id=athlete_id)
            db.session.add(profile)

        # Update profile fields
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

        # Log activity
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

# ================================
# Delete/Remove Athlete
# ================================

@coach_bp.route("/athlete/<int:athlete_id>", methods=["DELETE"])
@jwt_required()
def delete_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    try:
        # Soft delete - just deactivate the link
        link.is_active = False
        
        # Log activity
        athlete = User.query.get(athlete_id)
        activity = ActivityLog(
            user_id=identity,
            action="Removed athlete",
            details={"athlete_id": athlete_id, "athlete_name": athlete.name if athlete else "Unknown"},
            created_at=datetime.utcnow()
        )
        db.session.add(activity)
        
        db.session.commit()
        return jsonify({"msg": "Athlete removed successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error removing athlete: {str(e)}"}), 500

# ================================
# Get Athlete Statistics
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/stats", methods=["GET"])
@jwt_required()
def get_athlete_stats(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    try:
        # Get date range
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Workout statistics
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
        
        # Progress data
        latest_progress = AthleteProgress.query.filter_by(
            athlete_id=athlete_id
        ).order_by(desc(AthleteProgress.date)).first()
        
        # Active plans
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
            "active_plans": active_plans_count or 0,
            "period_days": days
        })
        
    except Exception as e:
        return jsonify({"msg": f"Error retrieving stats: {str(e)}"}), 500

# ================================
# Bulk Operations
# ================================

@coach_bp.route("/athletes/bulk-action", methods=["POST"])
@jwt_required()
def bulk_athlete_action():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    data = request.get_json()
    action = data.get("action")
    athlete_ids = data.get("athlete_ids", [])
    
    if not action or not athlete_ids:
        return jsonify({"msg": "Missing action or athlete IDs"}), 400
    
    try:
        success_count = 0
        
        if action == "assign_plan":
            plan_id = data.get("plan_id")
            if not plan_id:
                return jsonify({"msg": "Missing plan ID"}), 400
            
            for athlete_id in athlete_ids:
                # Verify relationship
                link = CoachAthlete.query.filter_by(
                    coach_id=identity,
                    athlete_id=athlete_id,
                    is_active=True
                ).first()
                
                if link:
                    # Check if plan already assigned
                    existing = AthletePlan.query.filter_by(
                        athlete_id=athlete_id,
                        plan_id=plan_id
                    ).first()
                    
                    if not existing:
                        athlete_plan = AthletePlan(
                            athlete_id=athlete_id,
                            plan_id=plan_id,
                            assigned_at=datetime.utcnow()
                        )
                        db.session.add(athlete_plan)
                        success_count += 1
        
        elif action == "deactivate":
            for athlete_id in athlete_ids:
                link = CoachAthlete.query.filter_by(
                    coach_id=identity,
                    athlete_id=athlete_id,
                    is_active=True
                ).first()
                
                if link:
                    link.is_active = False
                    success_count += 1
        
        db.session.commit()
        
        return jsonify({
            "msg": f"Bulk action completed successfully",
            "success_count": success_count
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error in bulk action: {str(e)}"}), 500

# ================================
# Export Athletes Data
# ================================

@coach_bp.route("/athletes/export", methods=["GET"])
@jwt_required()
def export_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    export_format = request.args.get('format', 'json')
    
    try:
        # Get all athletes
        athletes = db.session.query(
            User,
            AthleteProfile,
            func.count(WorkoutLog.id).label('total_workouts')
        ).join(
            CoachAthlete, CoachAthlete.athlete_id == User.id
        ).outerjoin(
            AthleteProfile, AthleteProfile.user_id == User.id
        ).outerjoin(
            WorkoutLog, WorkoutLog.athlete_id == User.id
        ).filter(
            CoachAthlete.coach_id == identity,
            CoachAthlete.is_active == True
        ).group_by(
            User.id, AthleteProfile.user_id
        ).all()
        
        athlete_data = []
        for athlete_record in athletes:
            user = athlete_record[0]
            profile = athlete_record[1]
            total_workouts = athlete_record[2]
            
            athlete_data.append({
                "name": user.name,
                "email": user.email,
                "status": user.status,
                "age": profile.age if profile else None,
                "gender": profile.gender if profile else None,
                "weight": profile.weight if profile else None,
                "height": profile.height if profile else None,
                "total_workouts": total_workouts
            })
        
        if export_format == 'csv':
            # Return CSV format
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=athlete_data[0].keys() if athlete_data else [])
            writer.writeheader()
            writer.writerows(athlete_data)
            
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=athletes_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        else:
            return jsonify(athlete_data)
            
    except Exception as e:
        return jsonify({"msg": f"Error exporting data: {str(e)}"}), 500

# ================================
# Send Message to Athlete
# ================================

@coach_bp.route("/athlete/<int:athlete_id>/message", methods=["POST"])
@jwt_required()
def send_message_to_athlete(athlete_id):
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    # Verify relationship
    link = CoachAthlete.query.filter_by(
        coach_id=identity,
        athlete_id=athlete_id,
        is_active=True
    ).first()
    
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    data = request.get_json()
    message_content = data.get("message")
    
    if not message_content:
        return jsonify({"msg": "Message content is required"}), 400
    
    try:
        from app.models import Message
        
        message = Message(
            sender_id=identity,
            receiver_id=athlete_id,
            content=message_content,
            sent_at=datetime.utcnow()
        )
        db.session.add(message)
        db.session.commit()
        
        return jsonify({"msg": "Message sent successfully"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Error sending message: {str(e)}"}), 500

# ================================
# Search Athletes
# ================================

@coach_bp.route("/athletes/search", methods=["GET"])
@jwt_required()
def search_athletes():
    identity = get_jwt_identity()
    if not is_coach(identity):
        return jsonify({"msg": "Unauthorized"}), 403

    search_term = request.args.get('q', '')
    
    if not search_term:
        return jsonify([])
    
    try:
        athletes = db.session.query(User).join(
            CoachAthlete, CoachAthlete.athlete_id == User.id
        ).filter(
            CoachAthlete.coach_id == identity,
            CoachAthlete.is_active == True,
            db.or_(
                User.name.ilike(f'%{search_term}%'),
                User.email.ilike(f'%{search_term}%')
            )
        ).limit(10).all()
        
        results = [
            {
                "id": athlete.id,
                "name": athlete.name,
                "email": athlete.email,
                "status": athlete.status
            }
            for athlete in athletes
        ]
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"msg": f"Error searching: {str(e)}"}), 500