from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app import db
from app.models.coach_athlete import CoachAthlete

athlete_bp = Blueprint("athlete", __name__)

# ---------------- Manage Athletes ----------------
@athlete_bp.route("/manage_athletes", endpoint="manage_athletes")
@jwt_required()
def manage_athletes():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    # Get athletes who have at least one coach
    athletes = (
        User.query.filter(User.role == "athlete")
        .join(CoachAthlete, User.id == CoachAthlete.athlete_id)
        .all()
    )

    coaches = User.query.filter_by(role='coach').all()
    return render_template("admin/manage_athletes.html", athletes=athletes, coaches=coaches)


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
