from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.athlete_goals import AthleteGoal
from app.models.goal_progress_log import GoalProgressLog
from . import athlete_bp
from datetime import date, datetime

# ---------------- API: Get all goals ----------------
@athlete_bp.route("/api/goals", methods=["GET"])
@jwt_required()
def get_goals():
    user_id = get_jwt_identity()
    goals = AthleteGoal.query.filter_by(athlete_id=user_id).all()

    result = []
    for g in goals:
        try:
            progress = round((g.current_value / g.target_value) * 100, 1) if g.target_value else 0
        except (TypeError, ZeroDivisionError):
            progress = 0
        
        # Ensure progress is within bounds
        progress = max(0, min(100, progress))
        
        # Determine status based on progress
        if progress >= 100:
            status = "completed"
        elif g.current_value > 0:
            status = "in progress"
        else:
            status = "not started"
        
        # Get progress log data for charting
        progress_logs = GoalProgressLog.query.filter_by(goal_id=g.id).order_by(GoalProgressLog.recorded_at.asc()).all()
        log_data = [{
            "value": log.recorded_value,
            "date": log.recorded_at.isoformat()
        } for log in progress_logs]
        
        # Get priority from goal or default to medium
        priority = getattr(g, 'priority', 'medium') or 'medium'
        
        # Get description
        description = getattr(g, 'description', '') or ''

        result.append({
            "id": g.id,
            "title": g.title,
            "target": g.target_value,
            "current_value": g.current_value,
            "progress": progress,
            "unit": g.unit,
            "due_date": g.deadline.isoformat() if g.deadline else None,
            "status": status,
            "tags": g.tags.split(",") if g.tags else [],
            "priority": priority,
            "description": description,
            "created_at": g.created_at.isoformat(),
            "image_url": g.image_url,
            "log_data": log_data
        })
    return jsonify(result)


# ---------------- API: Create goal ----------------
@athlete_bp.route("/api/goals", methods=["POST"])
@jwt_required()
def create_goal():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Validate required fields
    title = data.get("title")
    target = data.get("target")

    if not title or target is None:
        return jsonify({"msg": "Title and target are required"}), 400

    try:
        target_value = float(target)
        if target_value <= 0:
            return jsonify({"msg": "Target must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid target value"}), 400

    # Parse deadline
    deadline = None
    if data.get("due_date"):
        try:
            deadline = date.fromisoformat(data["due_date"])
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400

    # Create goal
    goal = AthleteGoal(
        athlete_id=user_id,
        title=title,
        target_value=target_value,
        current_value=float(data.get("current_value", 0.0)),
        unit=data.get("unit", ""),
        deadline=deadline,
        tags=data.get("tags", ""),
        image_url=data.get("image_url")
    )
    
    # Set priority if exists in model
    if hasattr(goal, 'priority'):
        goal.priority = data.get("priority", "medium")
    
    # Set description if exists in model
    if hasattr(goal, 'description'):
        goal.description = data.get("description", "")
    
    db.session.add(goal)
    db.session.flush()  # Get goal.id before committing
    
    # Log the initial progress with proper values
    initial_progress = 0.0  # Start at 0%
    initial_log = GoalProgressLog(
        goal_id=goal.id,
        recorded_value=0.0,
        progress=initial_progress,  # Set progress to 0
        created_at=datetime.utcnow(),
        recorded_at=datetime.utcnow()
    )
    db.session.add(initial_log)
    db.session.commit()
    
    return jsonify({"msg": "Goal created", "id": goal.id}), 201


# ---------------- API: Update goal ----------------
@athlete_bp.route("/api/goals/<int:goal_id>", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    user_id = get_jwt_identity()
    goal = AthleteGoal.query.filter_by(id=goal_id, athlete_id=user_id).first_or_404()
    data = request.get_json()

    # Update basic fields
    goal.title = data.get("title", goal.title)
    
    # Update target value
    if data.get("target"):
        try:
            target_value = float(data["target"])
            if target_value <= 0:
                return jsonify({"msg": "Target must be greater than 0"}), 400
            goal.target_value = target_value
        except (ValueError, TypeError):
            return jsonify({"msg": "Invalid target value"}), 400
    
    goal.unit = data.get("unit", goal.unit)
    goal.tags = data.get("tags", goal.tags)
    goal.image_url = data.get("image_url", goal.image_url)
    
    # Update priority if exists
    if hasattr(goal, 'priority'):
        goal.priority = data.get("priority", goal.priority)
    
    # Update description if exists
    if hasattr(goal, 'description'):
        goal.description = data.get("description", goal.description)

    # Parse deadline
    if data.get("due_date"):
        try:
            goal.deadline = date.fromisoformat(data["due_date"])
        except ValueError:
            return jsonify({"msg": "Invalid date format"}), 400
    
    # Update current value and log it if provided
    if data.get("current_value") is not None:
        try:
            new_current_value = float(data["current_value"])
            goal.current_value = new_current_value
            
            # Calculate progress
            progress = round((goal.current_value / goal.target_value) * 100, 1) if goal.target_value else 0
            progress = max(0, min(100, progress))  # Ensure between 0-100
            
            # Create log entry
            new_log = GoalProgressLog(
                goal_id=goal.id,
                recorded_value=goal.current_value,
                progress=progress,
                created_at=datetime.utcnow(),
                recorded_at=datetime.utcnow()
            )
            db.session.add(new_log)
        except (ValueError, TypeError):
            return jsonify({"msg": "Invalid current value"}), 400

    db.session.commit()
    return jsonify({"msg": "Goal updated"})


# ---------------- API: Delete goal ----------------
@athlete_bp.route("/api/goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    user_id = get_jwt_identity()
    goal = AthleteGoal.query.filter_by(id=goal_id, athlete_id=user_id).first_or_404()
    
    # Deleting the goal will also delete all associated logs due to cascade
    db.session.delete(goal)
    db.session.commit()
    return jsonify({"msg": "Goal deleted"})


# ---------------- API: Update a single goal's value (Quick Update) ----------------
@athlete_bp.route("/api/goals/<int:goal_id>/update_value", methods=["POST"])
@jwt_required()
def update_goal_value(goal_id):
    user_id = get_jwt_identity()
    goal = AthleteGoal.query.filter_by(id=goal_id, athlete_id=user_id).first_or_404()
    data = request.get_json()
    
    value_to_add = data.get("value_to_add")
    
    # Validate input
    if value_to_add is None:
        return jsonify({"msg": "value_to_add is required"}), 400
    
    try:
        value_to_add = float(value_to_add)
        if value_to_add <= 0:
            return jsonify({"msg": "Value must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid value"}), 400
    
    # Update current value
    goal.current_value += value_to_add
    
    # Calculate progress
    progress = round((goal.current_value / goal.target_value) * 100, 1) if goal.target_value else 0
    progress = max(0, min(100, progress))  # Ensure between 0-100
    
    # Create a new log entry
    new_log = GoalProgressLog(
        goal_id=goal.id,
        recorded_value=goal.current_value,
        progress=progress,
        created_at=datetime.utcnow(),
        recorded_at=datetime.utcnow()
    )
    db.session.add(new_log)
    db.session.commit()
    
    return jsonify({
        "msg": "Goal value updated",
        "current_value": goal.current_value,
        "progress": progress
    })