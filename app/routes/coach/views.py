from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash
from flask_jwt_extended import JWTManager
from flask import current_app

from app import db
from app.models.user import User
from app.schemas.user import UserSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.models import User, CoachAthlete, TrainingPlan, Feedback, WorkoutLog, TrainingGroup, AthleteGroup, ActivityLog, Subscription, WorkoutFile, ReadinessScore, MLInsight, Message

coach_bp = Blueprint('coach', __name__)



######### Coach Management Routes #########
@coach_bp.route("/manage_coachs")
@jwt_required()
def manage_coachs():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return "Unauthorized", 403

    coaches = User.query.filter_by(role="coach").all()
    coach_count = User.query.filter_by(role='coach').count()
    active_count = User.query.filter_by(role='coach', status='active').count()
    suspended_count = User.query.filter_by(role='coach', status='suspended').count()
    return render_template("admin/manage_coachs.html",
                        coaches=coaches,
                        coach_count=coach_count,
                        active_count=active_count,
                        suspended_count=suspended_count)

@coach_bp.route("/add", methods=["POST"])
@jwt_required()
def add_coach():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        if not current_user or current_user.role != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            return jsonify({"msg": "Missing fields"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"msg": "Email already registered"}), 400

        new_coach = User(
            name=name,
            email=email,
            role="coach",
            status='active',
            password_hash=generate_password_hash(password)
        )

        db.session.add(new_coach)
        db.session.commit()

        return jsonify({"msg": "Coach added successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Server error: {str(e)}"}), 500
    

@coach_bp.route("/edit_coach/<int:id>", methods=["GET", "POST"])
@jwt_required()
def edit_coach(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)

    if request.method == "POST":
        data = request.get_json()
        coach.name = data.get("name", coach.name)
        coach.email = data.get("email", coach.email)
        db.session.commit()
        return jsonify({"msg": "Coach updated successfully"}), 200

    return jsonify({
        "id": coach.id,
        "name": coach.name,
        "email": coach.email
    }), 200


@coach_bp.route("/delete_coach/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_coach(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)

    db.session.delete(coach)
    db.session.commit()

    return jsonify({"msg": "Coach deleted successfully"}), 200

@coach_bp.route("/toggle_coach_active/<int:id>", methods=["PATCH"])
@jwt_required()
def toggle_coach_active(id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user or current_user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.get_or_404(id)
    if coach.status == 'active':
        coach.status = 'suspended'
    else:
        coach.status = 'active'
    db.session.add(coach)
    db.session.commit()

    return jsonify({
        "msg": f"Coach {'activated' if coach.status == 'active' else 'deactivated'} successfully",
        "status": coach.status
    }), 200

@coach_bp.route("/view_athletes/<int:coachId>", methods=["GET"])
@jwt_required()
def view_athletes(coachId):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)

        # التأكد إن المستخدم admin
        if not current_user or current_user.role != "admin":
            return jsonify({"msg": "Unauthorized"}), 403

        # جلب المدرب
        coach = User.query.get(coachId)
        if not coach:
            return jsonify({"msg": "Coach not found"}), 404

        # جلب الرياضيين المرتبطين بالمدرب
        # هنفترض إن في علاقة في موديل User اسمها athletes
        athletes = [
            {"id": athlete.id, "name": athlete.name, "email": athlete.email}
            for athlete in coach.athletes
        ]

        return jsonify({"athletes": athletes}), 200
    except Exception as e:
        return jsonify({"msg": f"Server error: {str(e)}"}), 500


@coach_bp.route("/update_coach/<int:id>", methods=["PUT"])
@jwt_required()
def update_coach(id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or not user.is_superadmin:
        return jsonify({"msg": "Only super admin can update coaches"}), 403

    data = request.get_json()

    coach = User.query.filter_by(id=id, role="coach").first()
    if not coach:
        return jsonify({"msg": "Coach not found"}), 404

    coach.permissions = data.get("permissions", coach.permissions)

    db.session.commit()
    return jsonify({"msg": "Coach updated successfully"}), 200

@coach_bp.route("/get_coach/<int:id>")
@jwt_required()
def get_coach(id):
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or not user.is_superadmin:
        return jsonify({"msg": "Unauthorized"}), 403

    coach = User.query.filter_by(id=id, role="coach").first()
    if not coach:
        return jsonify({"msg": "Coach not found"}), 404

    return jsonify({
        "permissions": coach.permissions,
    })

@coach_bp.route("/some-coach-protected-route")
@jwt_required()
def coach_protected_area():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if "manage_users" not in user.permissions:
        return "Unauthorized", 403

    # allowed logic here


@coach_bp.route("/coach_profile")
@jwt_required()
def coach_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("coaches-profile.html", user=user)

@coach_bp.route("/coach_image")
@jwt_required()
def coach_image_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    return render_template("shared/base.html", user=user)

@coach_bp.route("/coach_profile", methods=["POST"])
@jwt_required()
def update_coach_profile():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    user.name = data.get("name")
    db.session.commit()
    return redirect(url_for("admin.coach_profile"))

@coach_bp.route("/coach_update-password", methods=["POST"])
@jwt_required()
def update_coach_password():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    data = request.form
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not user.check_password(current_password):
        return jsonify({"msg": "Wrong current password"}), 400

    if new_password != confirm_password:
        return jsonify({"msg": "Passwords do not match"}), 400

    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": "Password updated successfully"}), 200



########## Coach Athlete Management Routes #########
@coach_bp.route("/athletes", methods=["GET"])
@jwt_required()
def get_coach_athletes():
    identity = get_jwt_identity()
    coach = User.query.get(identity)

    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = (
        db.session.query(User.id, User.name)
        .join(CoachAthlete, CoachAthlete.athlete_id == User.id)
        .filter(CoachAthlete.coach_id == coach.id)
        .all()
    )

    return jsonify([{"id": a.id, "name": a.name} for a in athletes])

@coach_bp.route("/athlete/<int:athlete_id>/progress", methods=["GET"])
@jwt_required()
def get_athlete_progress(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)

    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    # validate athlete belongs to this coach
    link = CoachAthlete.query.filter_by(coach_id=coach.id, athlete_id=athlete_id).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    range_param = request.args.get("range", "month")

    # mock values – replace with ML/DB queries
    data = {
        "total_sessions": 24,
        "compliance": 92,
        "compliance_label": "Excellent",
        "avg_readiness": 8.5,
        "injury_alerts": 3,
        "performance_labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
        "performance_values": [11.5, 11.3, 11.1, 11.0],
        "readiness_values": [7, 8, 9, 8],
        "logs": [
            {"date": "2025-08-17", "session_type": "Sprint", "duration": "45 min", 
             "metric": "11.2s", "status": "Completed", "status_color": "success", 
             "feedback_action": "View"},
            {"date": "2025-08-16", "session_type": "Strength", "duration": "60 min", 
             "metric": "100kg Squat", "status": "Partial", "status_color": "warning", 
             "feedback_action": "Add"}
        ],
        "activities": [
            {"time": "32 min", "color": "success", 
             "text": '<strong>Leslie</strong> completed "Sprint Training".'},
            {"time": "56 min", "color": "danger", 
             "text": "High injury risk detected for <strong>John</strong>."}
        ]
    }
    return jsonify(data)

@coach_bp.route("/athlete/<int:athlete_id>/logs", methods=["GET"])
@jwt_required()
def get_athlete_logs(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)

    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    # validate athlete ownership
    link = CoachAthlete.query.filter_by(coach_id=coach.id, athlete_id=athlete_id).first()
    if not link:
        return jsonify({"msg": "Not your athlete"}), 403

    logs = WorkoutLog.query.filter_by(athlete_id=athlete_id).all()

    return jsonify([
        {
            "date": log.date.strftime("%Y-%m-%d"),
            "session_type": log.session_type,
            "duration": f"{log.duration} min",
            "metric": log.metric,
            "status": log.status,
            "status_color": "success" if log.status == "Completed" else "warning",
            "feedback_action": "View" if log.feedback else "Add"
        }
        for log in logs
    ])

@coach_bp.route("/athlete/<int:athlete_id>/plans", methods=["GET"])
@jwt_required()
def get_athlete_plans(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)

    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    plans = TrainingPlan.query.filter_by(athlete_id=athlete_id).all()
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "start": p.start_date.isoformat(),
            "end": p.end_date.isoformat(),
            "status": p.status
        }
        for p in plans
    ])


@coach_bp.route("/create_plan", methods=["GET", "POST"])
@jwt_required()
def create_plan():
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    if request.method == "POST":
        data = request.form
        plan = TrainingPlan(
            athlete_id=data.get("athlete_id"),
            coach_id=coach.id,
            title=data.get("title"),
            description=data.get("description"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            status="active"
        )
        db.session.add(plan)
        db.session.commit()
        flash("Plan created successfully!", "success")
        return redirect(url_for("coach.manage_plans"))

    athletes = User.query.filter_by(role="athlete").all()
    return render_template("coach/create_plan.html", athletes=athletes)

# manage plans


@coach_bp.route("/api/plans", methods=["GET"])
@jwt_required()
def get_plans_api():
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    plans = TrainingPlan.query.filter_by(coach_id=coach.id).all()
    
    return jsonify([
        {
            "id": p.id,
            "title": p.title,
            "athlete": p.athlete.name if p.athlete else "Unassigned",
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "status": p.status
        }
        for p in plans
    ])

@coach_bp.route("/plans", methods=["GET"])
@jwt_required()
def manage_plans():
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return redirect(url_for("auth.login"))

    plans = TrainingPlan.query.filter_by(coach_id=coach.id).all()
    return render_template("coach/manage_plans.html", plans=plans)


@coach_bp.route("/plans/<int:plan_id>/duplicate", methods=["POST"])
@jwt_required()
def duplicate_plan(plan_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    plan = TrainingPlan.query.get(plan_id)
    if not plan:
        return jsonify({"msg": "Plan not found"}), 404

    new_plan = TrainingPlan(
        athlete_id=plan.athlete_id,
        coach_id=plan.coach_id,
        title=plan.title + " (Copy)",
        start_date=plan.start_date,
        end_date=plan.end_date,
        status=plan.status
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify({"msg": "Plan duplicated", "id": new_plan.id}), 201

@coach_bp.route("/athlete/<int:athlete_id>/activity", methods=["GET"])
@jwt_required()
def get_activity_feed(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)

    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    # Example mocked
    activities = [
        {"time": "32 min", "color": "success", "text": 'Athlete completed Sprint session'},
        {"time": "2 hrs", "color": "primary", "text": 'You sent feedback on Jump Test'}
    ]

    return jsonify(activities)



@coach_bp.route("/athlete/<int:athlete_id>/give_feedback", methods=["GET", "POST"])
@jwt_required()
def give_feedback(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    athlete = User.query.get_or_404(athlete_id)

    if request.method == "POST":
        feedback_text = request.form.get("feedback")
        fb = Feedback(
            athlete_id=athlete.id,
            coach_id=coach.id,
            text=feedback_text   # ← استخدمي text مش feedback
        )
        db.session.add(fb)
        db.session.commit()
        flash("Feedback submitted successfully!", "success")
        return redirect(url_for("coach.view_feedback", athlete_id=athlete.id))

    return render_template("coach/give_feedback.html", athlete=athlete)




# Athletes
@coach_bp.route("/manage_athletes")
@jwt_required()
def manage_athletes():
    return render_template("coach/manage_athletes.html")

@coach_bp.route("/progress_tracking")
@jwt_required()
def progress_tracking():
    return render_template("coach/progress_tracking.html")

@coach_bp.route("/athlete_compliance")
@jwt_required()
def athlete_compliance():
    return render_template("coach/athlete_compliance.html")

# Training Plans



@coach_bp.route("/calendar")
@jwt_required()
def calendar():
    return render_template("coach/calendar.html")

# Feedback



@coach_bp.route("/athlete/<int:athlete_id>/feedback", methods=["GET"])
@jwt_required()
def view_feedback(athlete_id):
    identity = get_jwt_identity()
    coach = User.query.get(identity)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    athlete = User.query.get_or_404(athlete_id)

    feedbacks = Feedback.query.filter_by(athlete_id=athlete.id).order_by(Feedback.created_at.desc()).all()

    return render_template("coach/view_feedback.html", athlete=athlete, feedbacks=feedbacks)

@coach_bp.route("/feedback/select")
@jwt_required()
def select_athlete_for_feedback():
    coach = User.query.get(get_jwt_identity())
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = [link.athlete for link in coach.athlete_links]  # حسب علاقتك
    return render_template("coach/select_feedback.html", athletes=athletes)

@coach_bp.route("/athlete/<int:athlete_id>/profile")
def athlete_profile(athlete_id):
    athlete = User.query.get_or_404(athlete_id)
    return render_template("coach/athlete_profile.html", athlete=athlete)
