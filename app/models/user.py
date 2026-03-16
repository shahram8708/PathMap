from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from ..extensions import db, login_manager


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    last_active = db.Column(db.DateTime, nullable=True)
    total_logins = db.Column(db.Integer, default=0, nullable=False)

    # Email verification
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Subscription / premium
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    subscription_tier = db.Column(db.String(50), default='free', nullable=False)
    subscription_expires = db.Column(db.DateTime, nullable=True)
    razorpay_customer_id = db.Column(db.String(100), nullable=True)
    razorpay_subscription_id = db.Column(db.String(100), nullable=True)
    subscription_cancel_requested = db.Column(db.Boolean, default=False, nullable=False)

    # Onboarding
    onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)
    current_role_id = db.Column(db.Integer, nullable=True)
    years_experience = db.Column(db.Integer, nullable=True)
    pivot_motivation = db.Column(db.String(300), nullable=True)
    profile_photo_url = db.Column(db.String(500), nullable=True)
    notification_preferences = db.Column(db.JSON, default=dict)

    # Roles / flags
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_journey_provider = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    gdpr_deletion_requested = db.Column(db.Boolean, default=False, nullable=False)
    gdpr_deletion_requested_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash and store the password using pbkdf2:sha256 with salt."""
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )

    def check_password(self, password):
        """Verify a plain-text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def generate_verification_token(self):
        """
        Generate a URL-safe timed token for email verification.
        Token expires in 24 hours (86400 seconds).
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id, 'purpose': 'verify'}, salt='email-verification')

    @staticmethod
    def verify_verification_token(token, max_age=86400):
        """
        Validate an email verification token.
        Returns the User object if valid, None otherwise.
        max_age defaults to 24 hours.
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='email-verification', max_age=max_age)
        except Exception:
            return None
        if data.get('purpose') != 'verify':
            return None
        return User.query.get(data.get('user_id'))

    def generate_reset_token(self):
        """
        Generate a URL-safe timed token for password reset.
        Token expires in 1 hour (3600 seconds).
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(
            {'user_id': self.id, 'purpose': 'reset', 'hash_fragment': self.password_hash[-8:]},
            salt='password-reset'
        )

    @staticmethod
    def verify_reset_token(token, max_age=3600):
        """
        Validate a password reset token.
        Returns the User object if valid, None otherwise.
        The hash_fragment ensures the token is invalidated after password change.
        max_age defaults to 1 hour.
        """
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset', max_age=max_age)
        except Exception:
            return None
        if data.get('purpose') != 'reset':
            return None
        user = User.query.get(data.get('user_id'))
        if user is None:
            return None
        if user.password_hash[-8:] != data.get('hash_fragment'):
            return None
        return user

    @property
    def display_name(self):
        """Return first_name if set, otherwise the part before @ in email."""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0].capitalize()

    @property
    def is_subscription_active(self):
        """Check if premium subscription is currently active."""
        if not self.is_premium:
            return False
        if self.subscription_expires is None:
            return True
        return self.subscription_expires > datetime.utcnow()


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return User.query.get(int(user_id))
