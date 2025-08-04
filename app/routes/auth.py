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

@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = 'athlete'
    
    is_active = False

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 400

    new_user = User(email=email, role=role, name=name, is_active=is_active)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "Registered successfully. Please wait for admin approval."}), 201

@auth_bp.route("/register-pending")
def register_pending():
    return render_template("register-pending.html")


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
    
    if not user.is_active:
        return jsonify({'msg': 'Account is inactive. Please wait for admin approval.'}), 403
    
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


