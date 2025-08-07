from flask import Blueprint, render_template, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app import db

athlete_bp = Blueprint("athlete", __name__)

@athlete_bp.route("/manage_athletes", endpoint="manage_athletes")
@jwt_required()
def manage_athletes():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = User.query.filter(
    User.role == "athlete",
    User.coach_id.isnot(None)
    ).all()
    coaches = User.query.filter_by(role='coach').all()


    return render_template("admin/manage_athletes.html", athletes=athletes, coaches=coaches)


@athlete_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def get_athlete(id):
    athlete = User.query.get_or_404(id)
    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400
    return jsonify({"id": athlete.id, "name": athlete.name, "email": athlete.email})


@athlete_bp.route("/add", methods=["POST"])
@jwt_required()
def add_athlete():
    data = request.form
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"msg": "Missing fields"}), 400

    athlete = User(name=name, email=email, role="athlete")
    athlete.set_password(password)
    db.session.add(athlete)
    db.session.commit()

    return jsonify({"msg": "Athlete added successfully"}), 201


@athlete_bp.route("/<int:id>/update", methods=["POST"])
@jwt_required()
def update_athlete(id):
    data = request.get_json()
    athlete = User.query.get_or_404(id)

    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    athlete.name = data.get("name", athlete.name)
    coach_id = data.get("coach_id")
    athlete.coach_id = int(coach_id) if coach_id else None 
    db.session.commit()
    return jsonify({"msg": "Athlete updated successfully"}), 200


@athlete_bp.route("/<int:id>/delete", methods=["DELETE"])
@jwt_required()
def delete_athlete(id):
    athlete = User.query.get_or_404(id)

    if athlete.role != "athlete":
        return jsonify({"msg": "Invalid role"}), 400

    db.session.delete(athlete)
    db.session.commit()
    return jsonify({"msg": "Athlete deleted successfully"}), 200



###### Unassigned Athletes Management ######

@athlete_bp.route("/unassigned_athletes", endpoint="unassigned_athletes")
@jwt_required()
def get_unassigned_athletes():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    # Get all athletes with no coach assigned
    unassigned_athletes = User.query.filter_by(role="athlete", coach_id=None).all()
    coaches = User.query.filter_by(role="coach", is_active=True).all()

    return render_template("admin/unassigned_athletes.html", athletes=unassigned_athletes, coaches=coaches)


@athlete_bp.route("/unassigned")
@jwt_required()
def get_unassigned_athletes():
    identity = get_jwt_identity()
    user = User.query.get(identity)

    if not user or user.role != "admin":
        return jsonify({"msg": "Unauthorized"}), 403

    athletes = User.query.filter_by(role="athlete", coach_id=None).all()
    coaches = User.query.filter_by(role="coach", is_active=True).all()
    return render_template("admin/unassigned.html", athletes=athletes, coaches=coaches)



@athlete_bp.route("/assign_coach", methods=["POST"])
@jwt_required()
def assign_coach():
    data = request.get_json()
    coach_id = data.get("coach_id")
    athlete_id = data.get("athlete_id")

    athlete = User.query.get(athlete_id)
    coach = User.query.get(coach_id)

    if not athlete or athlete.role != "athlete":
        return jsonify({"msg": "Invalid athlete"}), 400
    if not coach or coach.role != "coach":
        return jsonify({"msg": "Invalid coach"}), 400

    print("Assigning athlete", athlete_id, "to coach", coach_id)

    athlete.coach_id = coach_id
    db.session.commit()

    return jsonify({"msg": "Coach assigned successfully!"}), 200
