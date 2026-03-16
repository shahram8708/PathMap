import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-secret-change-this')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.mailtrap.io')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@pathmap.in')

    # Razorpay (INR only — used in later steps)
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    # Defaults keep checkout working even if plan IDs are not pre-configured
    RAZORPAY_MONTHLY_PRICE_PAISE = int(os.environ.get('RAZORPAY_MONTHLY_PRICE_PAISE', '149900'))
    RAZORPAY_ANNUAL_PRICE_PAISE = int(os.environ.get('RAZORPAY_ANNUAL_PRICE_PAISE', '1199900'))

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    # Session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    REMEMBER_COOKIE_DURATION = timedelta(days=365)

    # Rate limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '200 per day;50 per hour'


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///pathmap_dev.db')
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_MONTHLY_PLAN_ID = os.environ.get('RAZORPAY_MONTHLY_PLAN_ID', 'plan_monthly_placeholder')
    RAZORPAY_ANNUAL_PLAN_ID = os.environ.get('RAZORPAY_ANNUAL_PLAN_ID', 'plan_annual_placeholder')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@pathmap.in')


class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')
    RAZORPAY_MONTHLY_PLAN_ID = os.environ.get('RAZORPAY_MONTHLY_PLAN_ID', 'plan_monthly_placeholder')
    RAZORPAY_ANNUAL_PLAN_ID = os.environ.get('RAZORPAY_ANNUAL_PLAN_ID', 'plan_annual_placeholder')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@pathmap.in')


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
