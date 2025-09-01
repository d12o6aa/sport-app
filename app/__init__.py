# app/__init__.py
from flask import Flask
from flask_cors import CORS
from app.extensions import db, ma, jwt, migrate
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import User, Subscription, WorkoutFile

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

    # استيراد الـ Blueprints
    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin.admin import admin_bp
    from app.routes.coach.views import coach_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.player import athlete_bp

    # تسجيل الـ Blueprints
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
