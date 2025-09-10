from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app import db
from app.models.coach_athlete import CoachAthlete

from . import athlete_bp



# ---------------- Manage Athletes ----------------
@athlete_bp.route("/manage_athletes", endpoint="manage_athletes")
@jwt_required()
def manage_athletes():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = 10
    pagination = (
    User.query.filter(User.role == "athlete")
    .paginate(page=page, per_page=per_page, error_out=False)
)


    athletes = pagination.items
    athlete_count = pagination.total
    active_count = User.query.filter_by(role='athlete', status='active').count()
    suspended_count = User.query.filter_by(role='athlete', status='suspended').count()


    coaches = User.query.filter_by(role='coach').all()
    return render_template("admin/manage_athletes.html", athletes=athletes, coaches=coaches, athlete_count=athlete_count,
                            active_count=active_count, suspended_count=suspended_count, pagination=pagination)


# ---------------- Get Single Athlete ----------------
@athlete_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_athlete(id):
    athlete = User.query.get_or_404(id)
    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400
    return jsonify({"id": athlete.id, "name": athlete.name, "email": athlete.email})


# ---------------- Add Athlete ----------------
@athlete_bp.route("/add", methods=["POST"])
@jwt_required()
def add_athlete():
    data = request.form
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    coach_id = data.get("coach_id")

    if not all([name, email, password]):
        return jsonify({"msg": "Missing fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    # إنشاء اللاعب
    athlete = User(name=name, email=email, role="athlete", status="active")
    athlete.set_password(password)
    db.session.add(athlete)
    db.session.flush()  # توليد ID بدون commit نهائي

    # لو فيه كوتش مختار نربطه باللاعب
    if coach_id:
        coach = User.query.get(coach_id)
        if not coach or coach.role != "coach":
            return jsonify({"msg": "Invalid coach"}), 400
        link = CoachAthlete(coach_id=coach.id, athlete_id=athlete.id)
        db.session.add(link)

    db.session.commit()

    return jsonify({"msg": "Athlete added successfully", "id": athlete.id}), 201


# ---------------- Update Athlete ----------------
@athlete_bp.route("/<int:id>/update", methods=["POST"])
@jwt_required()
def update_athlete(id):
    data = request.get_json()
    athlete = User.query.get_or_404(id)

    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    athlete.name = data.get("name", athlete.name)
    coach_id = data.get("coach_id")

    # Update coach assignment
    if coach_id:
        coach = User.query.get(coach_id)
        if not coach or coach.role != "coach":
            return jsonify({"msg": "Invalid coach"}), 400

        # Remove old links
        CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()
        # Create new link
        db.session.add(CoachAthlete(coach_id=coach_id, athlete_id=athlete.id))
    else:
        # Remove coach link if None
        CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()

    db.session.commit()
    return jsonify({"msg": "Athlete updated successfully"}), 200


# ---------------- Delete Athlete ----------------
@athlete_bp.route("/<int:id>/delete", methods=["DELETE"])
@jwt_required()
def delete_athlete(id):
    athlete = User.query.get_or_404(id)

    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    # Remove relationships first
    CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()
    db.session.delete(athlete)
    db.session.commit()
    return jsonify({"msg": "Athlete deleted successfully"}), 200


# ---------------- Unassigned Athletes ----------------
@athlete_bp.route("/unassigned_athletes", endpoint="unassigned_athletes")
@jwt_required()
def get_unassigned_athletes():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    unassigned_athletes = (
        User.query.filter_by(role="athlete")
        .outerjoin(CoachAthlete, User.id == CoachAthlete.athlete_id)
        .filter(CoachAthlete.coach_id == None)
        .all()
    )

    coaches = User.query.filter_by(role="coach", status='active').all()
    return render_template("admin/unassigned_athletes.html", athletes=unassigned_athletes, coaches=coaches)


@athlete_bp.route("/unassigned")
@jwt_required()
def unassigned_count():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    unassigned_count = (
        User.query.filter_by(role='athlete')
        .outerjoin(CoachAthlete, User.id == CoachAthlete.athlete_id)
        .filter(CoachAthlete.coach_id == None)
        .count()
    )

    coaches = User.query.filter_by(role="coach", status='active').all()
    return render_template("admin/unassigned.html", athletes=unassigned_count, coaches=coaches)


# ---------------- Assign Coach ----------------
@athlete_bp.route("/assign_coach", methods=["POST"])
@jwt_required()
def assign_coach():
    data = request.get_json()
    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    if not coach_id or not athlete_id:
        return jsonify({"msg": "Missing coach_id or athlete_id"}), 400

    athlete = User.query.get(athlete_id)
    coach = User.query.get(coach_id)

    if not athlete or athlete.role != "athlete":
        return jsonify({"msg": "Invalid athlete"}), 400
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Invalid coach"}), 400

    # Remove any old link
    CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()

    # Create new coach-athlete link
    link = CoachAthlete(coach_id=coach.id, athlete_id=athlete.id)
    db.session.add(link)

    # Optional: Update athlete status
    athlete.status = 'active'

    db.session.commit()

    return jsonify({"msg": "Coach assigned successfully!"}), 200


# ---------------- Bulk Delete Athletes ----------------
@athlete_bp.route("/bulk_delete", methods=["POST"])
@jwt_required()
def bulk_delete_athletes():
    data = request.get_json()
    athlete_ids = data.get("athlete_ids", [])

    if not athlete_ids:
        return jsonify({"msg": "No athlete IDs provided"}), 400

    athletes = User.query.filter(User.id.in_(athlete_ids), User.role == "athlete").all()

    if not athletes:
        return jsonify({"msg": "No valid athletes found"}), 404

    for athlete in athletes:
        # Remove relationships first
        CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()
        db.session.delete(athlete)

    db.session.commit()
    return jsonify({"msg": f"Deleted {len(athletes)} athletes successfully!"}), 200

# ---------------- Bulk Update Athlete Roles ----------------
@athlete_bp.route("/bulk_update_role", methods=["POST"])
@jwt_required()
def bulk_update_athlete_roles():
    data = request.get_json()
    athlete_ids = data.get("athlete_ids", [])
    new_role = data.get("new_role")

    if not athlete_ids or not new_role:
        return jsonify({"msg": "Missing athlete IDs or new role"}), 400

    if new_role not in ["athlete", "coach", "admin"]:
        return jsonify({"msg": "Invalid role"}), 400

    athletes = User.query.filter(User.id.in_(athlete_ids), User.role == "athlete").all()

    if not athletes:
        return jsonify({"msg": "No valid athletes found"}), 404

    for athlete in athletes:
        athlete.role = new_role
        if new_role != "athlete":
            # Remove any coach-athlete links if role changes
            CoachAthlete.query.filter_by(athlete_id=athlete.id).delete()

    db.session.commit()
    return jsonify({"msg": f"Updated roles for {len(athletes)} athletes to {new_role} successfully!"}), 200

# ---------------- Search Athletes ----------------
@athlete_bp.route("/search", methods=["GET"])
@jwt_required()
def search_athletes():  
    query = request.args.get("q", "")
    if not query:
        return jsonify({"msg": "No search query provided"}), 400

    athletes = User.query.filter(
        User.role == "athlete",
        (User.name.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%"))
    ).all()

    results = [{"id": athlete.id, "name": athlete.name, "email": athlete.email} for athlete in athletes]
    return jsonify(results), 200

# ---------------- Filter Athletes by Status ----------------
@athlete_bp.route("/filter_by_status", methods=["GET"])
@jwt_required()
def filter_athletes_by_status():
    status = request.args.get("status", "")
    if status not in ["active", "suspended"]:
        return jsonify({"msg": "Invalid or missing status"}), 400

    athletes = User.query.filter_by(role="athlete", status=status).all()
    results = [{"id": athlete.id, "name": athlete.name, "email": athlete.email} for athlete in athletes]
    return jsonify(results), 200

# ---------------- Sort Athletes ----------------
@athlete_bp.route("/sort", methods=["GET"])
@jwt_required()
def sort_athletes():
    sort_by = request.args.get("by", "name")
    order = request.args.get("order", "asc")

    if sort_by not in ["name", "email", "status"]:
        return jsonify({"msg": "Invalid sort field"}), 400
    if order not in ["asc", "desc"]:
        return jsonify({"msg": "Invalid sort order"}), 400

    sort_column = getattr(User, sort_by)
    if order == "desc":
        sort_column = sort_column.desc()

    athletes = User.query.filter_by(role="athlete").order_by(sort_column).all()
    results = [{"id": athlete.id, "name": athlete.name, "email": athlete.email} for athlete in athletes]
    return jsonify(results), 200

# ---------------- Filter Athletes by Coach ----------------
@athlete_bp.route("/filter_by_coach", methods=["GET"])
@jwt_required()
def filter_athletes_by_coach():
    coach_id = request.args.get("coach_id", type=int)
    if not coach_id:
        return jsonify({"msg": "No coach ID provided"}), 400

    coach = User.query.get(coach_id)
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Invalid coach ID"}), 400

    athletes = (
        User.query.join(CoachAthlete, User.id == CoachAthlete.athlete_id)
        .filter(CoachAthlete.coach_id == coach_id, User.role == "athlete")
        .all()
    )

    results = [{"id": athlete.id, "name": athlete.name, "email": athlete.email} for athlete in athletes]
    return jsonify(results), 200

# ---------------- Reast Passwor ----------------
@athlete_bp.route("/<int:id>/reset_password", methods=["POST"])
@jwt_required()
def reset_athlete_password(id):
    data = request.get_json()
    new_password = data.get("new_password")

    if not new_password:
        return jsonify({"msg": "No new password provided"}), 400

    athlete = User.query.get_or_404(id)

    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    athlete.set_password(new_password)
    db.session.commit()
    return jsonify({"msg": "Password reset successfully"}), 200


@athlete_bp.route("/toggle_status/<int:id>", methods=["POST"])
@jwt_required()
def toggle_athlete_status(id):
    athlete = User.query.get_or_404(id)
    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    athlete.status = "active" if athlete.status == "suspended" else "suspended"
    db.session.commit()
    return jsonify({"msg": f"Athlete status changed to {athlete.status}"}), 200
