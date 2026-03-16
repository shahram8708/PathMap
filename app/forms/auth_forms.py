from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SubmitField, EmailField, TextAreaField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError
)
from ..models.user import User


class SignupForm(FlaskForm):
    first_name = StringField(
        'First Name',
        validators=[DataRequired(message='First name is required.'), Length(min=2, max=100)]
    )
    email = EmailField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message='Password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.')
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message='Please confirm your password.'),
            EqualTo('password', message='Passwords do not match.')
        ]
    )
    submit = SubmitField('Create My Account')

    def validate_email(self, field):
        """Check if email is already registered."""
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError('This email address is already registered. Please log in.')


class LoginForm(FlaskForm):
    email = EmailField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(message='Password is required.')]
    )
    remember_me = BooleanField('Keep me logged in for 7 days')
    submit = SubmitField('Log In')


class ForgotPasswordForm(FlaskForm):
    email = EmailField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    submit = SubmitField('Send Reset Link')


class ResendVerificationForm(FlaskForm):
    email = EmailField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    submit = SubmitField('Resend Verification Email')


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        'New Password',
        validators=[
            DataRequired(message='New password is required.'),
            Length(min=8, message='Password must be at least 8 characters long.')
        ]
    )
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(message='Please confirm your new password.'),
            EqualTo('password', message='Passwords do not match.')
        ]
    )
    submit = SubmitField('Reset My Password')


class ContactForm(FlaskForm):
    name = StringField(
        'Full Name',
        validators=[
            DataRequired(message='Your name is required.'),
            Length(max=100, message='Name must be under 100 characters.')
        ]
    )
    email = EmailField(
        'Email Address',
        validators=[
            DataRequired(message='Email address is required.'),
            Email(message='Please enter a valid email address.')
        ]
    )
    subject = StringField(
        'Subject',
        validators=[
            DataRequired(message='Please choose a subject.'),
            Length(max=200, message='Subject must be under 200 characters.')
        ]
    )
    message = TextAreaField(
        'Message',
        validators=[
            DataRequired(message='Message cannot be empty.'),
            Length(min=20, max=2000, message='Message should be between 20 and 2000 characters.')
        ]
    )
    submit = SubmitField('Send Message')


class OnboardingForm(FlaskForm):
    """CSRF-only form for onboarding wizard."""
    pass
