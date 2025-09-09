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

from . import coach_bp


###### Views #####
coach_bp.route("/view_plan/<int:plan_id>")
@jwt_required()
def view_plans():
    return render_template("coach/plans.html")


######### Coach Management Routes #########
@coach_bp.route("/manage_coachs")
@jwt_required()
def manage_coachs():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return "Unauthorized", 403

    page = request.args.get("page", 1, type=int)
    per_page = 10  # عدد الكوتشات في الصفحة

    pagination = User.query.filter_by(role="coach").paginate(page=page, per_page=per_page, error_out=False)

    coaches = pagination.items
    coach_count = pagination.total
    active_count = User.query.filter_by(role='coach', status='active').count()
    suspended_count = User.query.filter_by(role='coach', status='suspended').count()
    return render_template("admin/manage_coachs.html",
                        coaches=coaches,
                        coach_count=coach_count,
                        active_count=active_count,
                        suspended_count=suspended_count,
                        pagination=pagination)

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

@coach_bp.route("/view_athletes/<int:coach_id>", methods=["GET"])
@jwt_required()
def view_athletes(coach_id):
    coach = User.query.filter_by(id=coach_id, role="coach").first_or_404()

    athletes = [
        {
            "id": link.athlete.id,
            "name": link.athlete.name,
            "email": link.athlete.email
        }
        for link in coach.athlete_links
    ]

    return jsonify({"athletes": athletes})


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






# Athletes

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


@coach_bp.route("/bulk_delete", methods=["POST"])
@jwt_required()
def bulk_delete():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or not current_user.admin_profile or not current_user.admin_profile.is_superadmin:
        return jsonify({"msg": "Only super admin can delete users"}), 403

    data = request.get_json()
    ids = data.get("ids", [])

    if not ids:
        return jsonify({"msg": "No IDs provided"}), 400

    ids = [uid for uid in ids if uid != current_user.id]

    User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return jsonify({"msg": "Users deleted successfully"}), 200

@coach_bp.route("/bulk_change_role", methods=["POST"])
@jwt_required()
def bulk_change_role():
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or not current_user.admin_profile or not current_user.admin_profile.is_superadmin:
        return jsonify({"msg": "Only super admin can change roles"}), 403

    data = request.get_json()
    ids = data.get("ids", [])
    new_role = data.get("role")

    if not ids or not new_role:
        return jsonify({"msg": "IDs and new role are required"}), 400

    ids = [uid for uid in ids if uid != current_user.id]

    User.query.filter(User.id.in_(ids)).update({"role": new_role}, synchronize_session=False)
    db.session.commit()

    return jsonify({"msg": f"Users updated to {new_role} successfully"}), 200

@coach_bp.route("/reset_password/<int:user_id>", methods=["POST"])
@jwt_required()
def reset_password(user_id):
    identity = get_jwt_identity()
    current_user = User.query.get(identity)

    if not current_user or not current_user.admin_profile or not current_user.admin_profile.is_superadmin:
        return jsonify({"msg": "Only super admin can reset passwords"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    new_password = "Default@123"
    user.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": f"Password reset to {new_password}"}), 200
