import os
from datetime import timedelta

class Config:
    # إعدادات قاعدة البيانات
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # إعدادات JWT الآمنة
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # استخدام httpOnly cookies للـ JWT
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_COOKIE_SECURE = True  # تأكد من استخدام HTTPS في الإنتاج
    JWT_COOKIE_CSRF_PROTECT = True  # حماية CSRF
    JWT_COOKIE_SAMESITE = 'Lax'  # حماية من CSRF
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_COOKIE_DOMAIN = None  # سيتم تعيينه تلقائيًا
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:;"
    }
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_HEADERS_ENABLED = True
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_EXTENSIONS = ['.jpg', '.png', '.pdf', '.csv']
    
    # Password Policy
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL = True
    
    # Account Security
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION = timedelta(minutes=30)
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = 'logs/app.log'


class DevelopmentConfig(Config):
    DEBUG = True
    JWT_COOKIE_SECURE = False  # السماح بـ HTTP في التطوير
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    # في الإنتاج، تأكد من تعيين هذه المتغيرات من environment variables
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    # تأكد من HTTPS
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}