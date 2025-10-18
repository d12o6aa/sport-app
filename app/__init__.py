
from flask import Flask, jsonify, url_for, render_template
from flask_cors import CORS
from app.extensions import db, ma, jwt, migrate,socketio
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import User, Subscription, WorkoutFile
from app.filters import register_filters
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from sqlalchemy import desc 

scheduler = APScheduler()

def configure_scheduler(app):
    """تهيئة وبدء تشغيل المجدول (Scheduler)"""
    if not app.config.get('SCHEDULER_INITIALIZED', False):
        try:
            scheduler.init_app(app)
            scheduler.start()
            app.config['SCHEDULER_INITIALIZED'] = True
        except Exception as e:
            if "already initialized" not in str(e):
                raise


# --- HELPER FUNCTION: Collects real data for ML Model Input ---
def get_ml_input_data(athlete_id):
    """
    Collects the latest data points from the database needed for the ML model prediction.
    NOTE: This must run inside the Flask application context.
    """
    from app.models import WorkoutLog, AthleteProgress, ReadinessScore
    
    latest_workout = WorkoutLog.query.filter_by(athlete_id=athlete_id).order_by(desc(WorkoutLog.logged_at)).first()
    latest_progress = AthleteProgress.query.filter_by(athlete_id=athlete_id).order_by(desc(AthleteProgress.date)).first()
    latest_readiness = ReadinessScore.query.filter_by(athlete_id=athlete_id).order_by(desc(ReadinessScore.date)).first()

    # بناء قاموس الإدخال، مع توفير قيم افتراضية آمنة
    input_data = {
        # General/Physiological Data (Example mappings - adjust based on your actual model features)
        "heart_rate": getattr(latest_workout, 'average_heart_rate', 0),
        "sleep_hours": getattr(latest_readiness, 'sleep_hours', 7),
        "dietary_intake": getattr(latest_progress, 'calories_consumed', 2500),
        "training_days_per_week": getattr(latest_workout, 'training_days_per_week', 3),
        "recovery_days_per_week": getattr(latest_workout, 'recovery_days_per_week', 2),
        
        # Biometric Features (Assuming fields exist in your model/progress tables)
        "Heart_Rate_(HR)": getattr(latest_workout, 'average_heart_rate', 0),
        "Muscle_Tension_(MT)": getattr(latest_workout, 'muscle_tension', 0.5),
        "Body_Temperature_(BT)": getattr(latest_workout, 'body_temperature', 36.5),
        "Breathing_Rate_(BR)": getattr(latest_workout, 'breathing_rate', 16),
        "Blood_Pressure_Systolic_(BP)": getattr(latest_progress, 'blood_pressure_systolic', 120),
        "Blood_Pressure_Diastolic_(BP)": getattr(latest_progress, 'blood_pressure_diastolic', 80),
        
        # Other Training Metrics
        "Training_Duration_(TD)": getattr(latest_workout, 'actual_duration', 60),
        "Wavelet_Features_(WF)": getattr(latest_readiness, 'wavelet_features', 0.5),
        "Feature_Weights_(FW)": getattr(latest_readiness, 'feature_weights', 0.9),
        
        # Categorical Features
        "Training_Intensity_(TI)": getattr(latest_workout, 'intensity', "Medium"),
        "Training_Type_(TT)": getattr(latest_workout, 'workout_type', "Cardio"),
        "Time_Interval_(TI)": getattr(latest_workout, 'time_of_day', "Morning"),
        "Phase_of_Training_(PT)": getattr(latest_readiness, 'training_phase', "Build")
    }
    
    return input_data

def create_app():
    # --- FLASK SETUP ---
    app = Flask(__name__)
    app.app_context()

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
    
    # ✅ تهيئة APScheduler (فقط إذا لم يتم تهيئته بعد)
    if not scheduler.running:
        try:
            # Init the scheduler only once
            scheduler.init_app(app)
        except Exception as e:
            # Ignore if already initialized due to reloader
            if "already initialized" not in str(e):
                raise
    

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return render_template("auth/login.html")

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return render_template("auth/login.html")
    @jwt.unauthorized_loader 
    def unauthorized_callback(callback):
        return render_template("auth/login.html")
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
    from app.routes.prediction.service import predict_all

    # تسجيل الـ Blueprints
    app.register_blueprint(prediction_bp, url_prefix="/prediction")
    app.register_blueprint(athlete_bp, url_prefix="/athlete")
    app.register_blueprint(coach_bp, url_prefix="/coach")
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(home_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    
    # --- SCHEDULER JOB DEFINITION ---
    @scheduler.task('cron', id='daily_prediction_job', day='*', hour=3)
    def daily_prediction_job():
        from app.models import User, ReadinessScore, MLInsight, WorkoutLog, AthleteProgress
        
        with app.app_context():
            print(f"Running daily prediction job at {datetime.now()}...")
            athletes = User.query.filter_by(role='athlete', is_deleted=False).all()
            
            for athlete in athletes:
                try:
                    has_activity = WorkoutLog.query.filter_by(athlete_id=athlete.id).first()
                    if not has_activity:
                         continue
                         
                    input_data = get_ml_input_data(athlete.id)
                    result = predict_all(input_data)
                    
                    # Store Insight
                    new_insight = MLInsight(
                        athlete_id=athlete.id,
                        generated_at=datetime.utcnow(),
                        insight_data=result
                    )
                    db.session.add(new_insight)

                    # Store Readiness Score
                    new_readiness = ReadinessScore(
                        athlete_id=athlete.id,
                        date=datetime.utcnow().date(),
                        score=result.get("readiness_score"),
                        injury_risk=result.get("injury_severity_prediction")
                    )
                    db.session.add(new_readiness)
                    db.session.commit()
                    print(f"Prediction successful for athlete {athlete.id}")
                    
                except Exception as e:
                    print(f"Error in daily prediction job for athlete {athlete.id}: {e}")
                    db.session.rollback()

    # ✅ بدء Scheduler مع التحقق من عدم تشغيله مسبقًا (الحل النهائي)
    # نستخدم app.before_first_request لضمان بدء التشغيل مرة واحدة في بيئة الإنتاج/الاستضافة
    # ولكن هنا نستخدم الشرط العادي لتغطية وضع التطوير.
    if not scheduler.running:
        scheduler.start()
    
    return app

# JWT callback
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.get(identity)
