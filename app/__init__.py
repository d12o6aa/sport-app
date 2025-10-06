# app/__init__.py
import eventlet

eventlet.monkey_patch()

from flask import Flask, jsonify, url_for
from flask_cors import CORS
from app.extensions import db, ma, jwt, migrate,socketio
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import User, Subscription, WorkoutFile
from app.filters import register_filters

def create_app():
    app = Flask(__name__)

    # الإعدادات
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myapp_user:your_secure_password@localhost:5432/myapp_dev'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'jwt-secret'
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 36000
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False 
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False 

    # تهيئة الإضافات
    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/*": {
        "origins": ["http://127.0.0.1:5000", "http://localhost:3000"],
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "OPTIONS"]
    }})
    socketio.init_app(app, async_mode='eventlet')
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        # You can log the event here if you need to
        # app.logger.info("An expired token was used, redirecting to login.")
        
        # This will return a JSON response with a 401 status code
        # The frontend will be responsible for handling this response.
        return jsonify({
            "msg": "The session has expired. Please log in again.",
            "redirect_to": url_for("auth.login_page", _external=True) # Assuming your login route is named 'auth.login'
        }), 401

    # 🆕 Set up the handler for invalid tokens as well for consistency
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "msg": "The token is invalid. Please log in again.",
            "redirect_to": url_for("auth.login_page", _external=True)
        }), 401
    # context processor
    @app.context_processor
    def inject_user():
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            if identity:
                user = User.query.get(identity)
                return dict(user=user)
        except Exception:
            pass
        return dict(user=None)
    register_filters(app)
    # استيراد الـ Blueprints
    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin.admin import admin_bp
    from app.routes.coach import coach_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.player import athlete_bp
    from app.routes.prediction.routes import prediction_bp

    # تسجيل الـ Blueprints
    app.register_blueprint(prediction_bp, url_prefix="/prediction")
    app.register_blueprint(athlete_bp, url_prefix="/athlete")
    app.register_blueprint(coach_bp, url_prefix="/coach")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(home_bp)
    app.register_blueprint(user_bp, url_prefix="/user")

    return app

# JWT callback
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)

