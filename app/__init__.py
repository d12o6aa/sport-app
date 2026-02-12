from flask import Flask, redirect, url_for
from flask_cors import CORS
from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request
)
from flask import request
from app.extensions import db, ma, jwt, migrate, socketio
from app.filters import register_filters
from app.config import config
from app.models import User


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or app.config.get(
        "ENV", "development"
    )
    app.config.from_object(config[config_name])

    # Init extensions
    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, async_mode="eventlet")

    # CORS (configurable)
    CORS(
        app,
        supports_credentials=True,
        resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
    )

    # JWT callbacks
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return redirect(url_for("auth.login_page"))

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return redirect(url_for("auth.login_page"))

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return redirect(url_for("auth.login_page"))

    # Inject current user
    @app.context_processor
    def inject_user():
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                return {"user": User.query.get(identity)}
        except Exception:
            pass
        return {"user": None}

    register_filters(app)

    # Blueprints
    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin.admin import admin_bp
    from app.routes.coach import coach_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.player import athlete_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(coach_bp, url_prefix="/coach")
    app.register_blueprint(athlete_bp, url_prefix="/athlete")
    app.register_blueprint(dashboard_bp)

    @app.before_request
    def check_first_run():
        allowed_endpoints = ['admin.super_setup_page', 'admin.super_setup_post', 'static']
        
        if request.endpoint in allowed_endpoints:
            return

        try:
            if User.query.first() is None:
                return redirect(url_for('admin.super_setup_page'))
        except Exception:
            pass

    return app



@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)

