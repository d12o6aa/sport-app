from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity,JWTManager,get_jwt,set_access_cookies
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash


from app import db
from app.models.user import User
from app.schemas.user import UserSchema

auth_bp = Blueprint("auth", __name__)

user_schema = UserSchema()

@auth_bp.route("/register", methods=["POST"])
@jwt_required()
def register():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if not current_user:
        return jsonify({"msg": "Invalid creator"}), 403

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    # تحكم في الصلاحيات
    if current_user.role == "coach" and role != "athlete":
        return jsonify({"msg": "Coaches can only add athletes"}), 403
    elif current_user.role == "admin" and role not in ["admin", "coach"]:
        return jsonify({"msg": "Admins can only add coaches or admins"}), 403
    elif current_user.role != "admin" and current_user.role != "coach":
        return jsonify({"msg": "Unauthorized"}), 403

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    new_user = User(email=email, role=role, created_by_id=current_user.id)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return user_schema.jsonify(new_user), 201


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")  


@auth_bp.route("/login", methods=["POST"])
def login_post():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON"}), 400

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid email or password"}), 401

    print("User ID:", user.id, "Type:", type(user.id))
    if not isinstance(user.id, (int, str)):
        print("Invalid user ID type:", type(user.id))
        return jsonify({"msg": "Internal server error: Invalid user ID"}), 500
    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    session["access_token"] = access_token
    session["user_id"] = user.id
    session["role"] = user.role
    response = jsonify({"login": True})
    set_access_cookies(response, access_token)

    return response


