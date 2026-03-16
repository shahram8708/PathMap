from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session
)
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db, limiter
from ..models.user import User
from ..forms.auth_forms import SignupForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, ResendVerificationForm
from ..services.email_service import (
    send_verification_email, send_password_reset_email, send_welcome_email
)


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def signup():
    """
    Registration endpoint.
    GET: Render signup form.
    POST: Validate form, create user, send verification email, redirect to login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main_dashboard'))

    form = SignupForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        user = User(
            email=email,
            first_name=form.first_name.data.strip()
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        try:
            send_verification_email(user)
            flash(
                f'Account created! We sent a verification email to {email}. '
                f'Please verify your email before logging in.',
                'success'
            )
        except Exception:
            flash(
                'Account created! However, we could not send the verification email. '
                'Please use the "Resend Verification" option on the login page.',
                'warning'
            )

        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html', form=form, title='Create Account')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per 15 minutes')
def login():
    """
    Login endpoint.
    GET: Render login form.
    POST: Validate credentials, enforce email verification, log in user.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main_dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html', form=form, title='Log In')

        if not user.is_active:
            flash('This account has been deactivated. Please contact support@pathmap.in.', 'danger')
            return render_template('auth/login.html', form=form, title='Log In')

        if not user.is_verified:
            session['unverified_email'] = email
            flash(
                'Please verify your email address before logging in. '
                'Check your inbox or request a new verification email below.',
                'warning'
            )
            return redirect(url_for('auth.verify_pending'))

        user.last_login = datetime.utcnow()
        session.permanent = True

        login_user(user, remember=True, duration=timedelta(days=365))
        current_user.last_active = datetime.utcnow()
        current_user.total_logins = (current_user.total_logins or 0) + 1
        db.session.commit()

        flash(f'Welcome back, {user.display_name}!', 'success')

        if not user.onboarding_complete:
            return redirect(url_for('onboarding.onboarding_start'))

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        return redirect(url_for('dashboard.main_dashboard'))

    return render_template('auth/login.html', form=form, title='Log In')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log the current user out and redirect to homepage."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/verify/<token>')
def verify_email(token):
    """
    Validate the email verification token.
    Token is valid for 24 hours.
    On success: mark user as verified, send welcome email, redirect to login.
    On failure: show error flash and redirect to login.
    """
    user = User.verify_verification_token(token)

    if user is None:
        flash(
            'That verification link is invalid or has expired (links expire after 24 hours). '
            'Please request a new verification email.',
            'danger'
        )
        return redirect(url_for('auth.login'))

    if user.is_verified:
        flash('Your email is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    user.is_verified = True
    db.session.commit()

    try:
        send_welcome_email(user)
    except Exception:
        pass

    flash(
        'Your email has been verified successfully! Welcome to PathMap.',
        'success'
    )
    if not user.onboarding_complete:
        return redirect(url_for('onboarding.onboarding_start'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/verify-pending', methods=['GET', 'POST'])
def verify_pending():
    """
    Page shown to users who tried to login but haven't verified their email yet.
    POST: Resend verification email.
    """
    email = session.get('unverified_email')
    form = ResendVerificationForm()

    if form.validate_on_submit():
        email_input = form.email.data.lower().strip()
        user = User.query.filter_by(email=email_input).first()

        if user and not user.is_verified:
            try:
                send_verification_email(user)
                flash(
                    f'A new verification email has been sent to {email_input}. '
                    f'Please check your inbox and spam folder.',
                    'success'
                )
            except Exception:
                flash('Failed to send verification email. Please try again later.', 'danger')
        else:
            flash(
                'No unverified account found with that email address.',
                'warning'
            )
        return redirect(url_for('auth.verify_pending'))

    if email and not form.email.data:
        form.email.data = email

    return render_template(
        'auth/verify_pending.html',
        form=form,
        prefill_email=email,
        title='Verify Your Email'
    )


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('3 per hour')
def forgot_password():
    """
    GET: Render forgot password form.
    POST: If email exists, generate reset token and send reset email.
    Always show the same success message regardless of whether email exists
    (prevents user enumeration attacks).
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main_dashboard'))

    form = ForgotPasswordForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user and user.is_verified:
            try:
                send_password_reset_email(user)
            except Exception:
                pass

        flash(
            'If an account with that email address exists, '
            'we have sent a password reset link. It expires in 1 hour.',
            'info'
        )
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/forgot_password.html',
        form=form,
        title='Reset Your Password'
    )


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """
    GET: Validate token, render reset form.
    POST: Set new password, invalidate token, redirect to login.
    Token is single-use (invalidated when password changes) and expires in 1 hour.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.main_dashboard'))

    user = User.verify_reset_token(token)

    if user is None:
        flash(
            'That password reset link is invalid or has expired (links expire after 1 hour). '
            'Please request a new reset link.',
            'danger'
        )
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()

        flash(
            'Your password has been reset successfully. Please log in with your new password.',
            'success'
        )
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/reset_password.html',
        form=form,
        token=token,
        title='Set New Password'
    )
