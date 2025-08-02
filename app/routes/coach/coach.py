from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash, hash_password

from flask_jwt_extended import JWTManager
from flask import current_app

from app import db
from app.models.user import User
from app.schemas.user import UserSchema
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask import render_template

coach_bp = Blueprint("coach", __name__)


@coach_bp.route('/coach/add_athlete', methods=['POST'])
@jwt_required()
def add_athlete():
    current_user = get_jwt_identity()
    coach = User.query.get(current_user)

    if coach.role != 'coach':
        return jsonify({"msg": "Only coaches can add athletes"}), 403

    data = request.get_json()
    new_athlete = User(
        email=data['email'],
        password=hash_password(data['password']),
        role='athlete',
        coach_id=coach.id
    )
    db.session.add(new_athlete)
    db.session.commit()
    return jsonify({"msg": "Athlete added"}), 201
