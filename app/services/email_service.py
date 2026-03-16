from flask import current_app, render_template, url_for
from flask_mail import Message
from ..extensions import mail


def _send_email(recipient, subject, html_body):
    """
    Internal helper to send an email via Flask-Mail.
    Catches and logs errors silently in production to prevent broken UX.
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send email to {recipient}: {str(e)}')


def send_verification_email(user):
    """
    Send an email verification link to the newly registered user.
    Token expires in 24 hours.
    """
    token = user.generate_verification_token()
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    subject = 'Verify your PathMap email address'
    html_body = render_template(
        'emails/verification_email.html',
        user=user,
        verify_url=verify_url
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_password_reset_email(user):
    """
    Send a password reset link to the user.
    Token expires in 1 hour.
    """
    token = user.generate_reset_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    subject = 'Reset your PathMap password'
    html_body = render_template(
        'emails/password_reset.html',
        user=user,
        reset_url=reset_url
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_welcome_email(user):
    """
    Send a welcome email after the user verifies their email address.
    """
    subject = 'Welcome to PathMap — your career journey starts now'
    dashboard_url = url_for('dashboard.main_dashboard', _external=True)
    html_body = render_template(
        'emails/welcome_email.html',
        user=user,
        dashboard_url=dashboard_url
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_premium_welcome_email(user, plan_type, expires_at):
    subject = 'Welcome to PathMap Premium'
    dashboard_url = url_for('dashboard.main_dashboard', _external=True)
    html_body = render_template(
        'emails/premium_welcome.html',
        user=user,
        plan_type=plan_type,
        expires_at=expires_at,
        dashboard_url=dashboard_url
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_subscription_cancelled_email(user, expires_at):
    subject = 'Your PathMap Premium is scheduled to end'
    html_body = render_template(
        'emails/subscription_cancelled.html',
        user=user,
        expires_at=expires_at
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_payment_failed_email(user):
    subject = 'We could not process your PathMap renewal'
    billing_url = url_for('profile.billing_page', _external=True)
    html_body = render_template(
        'emails/payment_failed.html',
        user=user,
        billing_url=billing_url
    )
    _send_email(recipient=user.email, subject=subject, html_body=html_body)


def send_gdpr_deletion_confirmation_email(recipient_email, name):
    subject = 'Your PathMap account deletion is complete'
    html_body = render_template(
        'emails/gdpr_deletion_confirmation.html',
        name=name
    )
    _send_email(recipient=recipient_email, subject=subject, html_body=html_body)


def send_admin_notification(subject, body):
    recipient = current_app.config.get('ADMIN_ALERT_EMAIL')
    if not recipient:
        current_app.logger.warning('ADMIN_ALERT_EMAIL not configured; skipping admin notification')
        return
    html_body = render_template('emails/admin_notification.html', body=body)
    _send_email(recipient=recipient, subject=subject, html_body=html_body)

