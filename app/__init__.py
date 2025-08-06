from flask import Flask, g
from flask_cors import CORS
from app.models.user import User
from app.extensions import db, ma, jwt, migrate
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request




def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dev.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = 'jwt-secret'
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 36000
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False 
    app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False 

    
    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/*": {
        "origins": ["http://127.0.0.1:5000", "http://localhost:3000"],  # ضيف الـ frontend URL
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "OPTIONS"]
    }})
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

    from app.routes.home import home_bp
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.admin.admin import admin_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.player.athlete import athlete_bp
    app.register_blueprint(athlete_bp, url_prefix="/athlete")

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(home_bp)
    app.register_blueprint(user_bp, url_prefix="/user")

    
    with app.app_context():
        from app.models.user import User
        db.create_all()
    
    return app


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)
