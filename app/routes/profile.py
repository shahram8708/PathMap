from datetime import datetime, timedelta
import io
import json
from decimal import Decimal

from flask import Blueprint, render_template, url_for, flash, redirect, request, send_file, jsonify, current_app
from flask_login import login_required, current_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..forms.profile_forms import (
    UpdateProfileForm,
    ChangePasswordForm,
    NotificationPreferencesForm,
    GDPRDeletionForm,
    SimpleActionForm,
)
from ..models.assessment import UserAssessment
from ..models.analysis import SkillTransferAnalysis
from ..models.journey import Journey, JourneyView
from ..models.roadmap import PivotRoadmap, ProgressEntry
from ..models.session import ShadowSessionProvider, SessionBooking, ResourceBookmark, ProviderApplication
from ..models.payment import SubscriptionPayment
from ..models.role import Role
from ..models.user import User
from ..utils.decorators import admin_required
from ..services.email_service import send_gdpr_deletion_confirmation_email, send_admin_notification

profile_bp = Blueprint('profile', __name__, url_prefix='/profile-settings')


@profile_bp.route('/profile')
@login_required
def profile_page():
    assessment = (
        UserAssessment.query
        .filter_by(user_id=current_user.id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    saved_analyses_count = SkillTransferAnalysis.query.filter_by(user_id=current_user.id, is_saved=True).count()
    journey_count = Journey.query.filter_by(submitter_user_id=current_user.id, is_published=True).count()
    provider_profile = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first()
    active_roadmap = (
        PivotRoadmap.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(PivotRoadmap.created_at.desc())
        .first()
    )
    latest_payment = (
        SubscriptionPayment.query
        .filter_by(user_id=current_user.id)
        .order_by(SubscriptionPayment.payment_date.desc())
        .first()
    )
    member_since_days = (datetime.utcnow() - current_user.created_at).days if current_user.created_at else 0
    assessment_complete = assessment.is_fully_complete if assessment else False

    profile_points = 0
    if current_user.is_verified:
        profile_points += 10
    if current_user.onboarding_complete:
        profile_points += 10
    if assessment_complete:
        profile_points += 30
    if saved_analyses_count > 0:
        profile_points += 20
    if active_roadmap:
        profile_points += 20
    if journey_count > 0:
        profile_points += 10
    profile_completeness_pct = profile_points

    checkins_count = ProgressEntry.query.filter_by(user_id=current_user.id).count()
    journeys_read = JourneyView.query.filter_by(user_id=current_user.id).count()
    sessions_booked = SessionBooking.query.filter_by(booker_user_id=current_user.id).count()

    return render_template(
        'profile/profile.html',
        assessment=assessment,
        saved_analyses_count=saved_analyses_count,
        journey_count=journey_count,
        provider_profile=provider_profile,
        active_roadmap=active_roadmap,
        latest_payment=latest_payment,
        member_since_days=member_since_days,
        profile_completeness_pct=profile_completeness_pct,
        assessment_complete=assessment_complete,
        checkins_count=checkins_count,
        journeys_read=journeys_read,
        sessions_booked=sessions_booked,
        title='My Profile'
    )


@profile_bp.route('/settings')
@login_required
def settings_page():
    active_tab = request.args.get('tab', 'profile')
    update_form = UpdateProfileForm()
    password_form = ChangePasswordForm()
    notification_form = NotificationPreferencesForm()
    gdpr_form = GDPRDeletionForm()
    action_form = SimpleActionForm()

    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()
    update_form.current_role_id.choices = [(0, 'Not listed / Other')] + [(role.id, role.title) for role in roles]
    update_form.first_name.data = current_user.first_name or ''
    update_form.current_role_id.data = current_user.current_role_id or 0
    update_form.years_experience.data = current_user.years_experience

    prefs = current_user.notification_preferences or {}
    notification_form.email_weekly_checkin.data = prefs.get('email_weekly_checkin', False)
    notification_form.email_journey_published.data = prefs.get('email_journey_published', True)
    notification_form.email_session_updates.data = prefs.get('email_session_updates', True)
    notification_form.email_product_updates.data = prefs.get('email_product_updates', True)
    notification_form.email_marketing.data = prefs.get('email_marketing', False)

    return render_template(
        'profile/settings.html',
        update_form=update_form,
        password_form=password_form,
        notification_form=notification_form,
        gdpr_form=gdpr_form,
        action_form=action_form,
        active_tab=active_tab,
        razorpay_key_id=current_app.config.get('RAZORPAY_KEY_ID'),
        title='Settings'
    )


@profile_bp.route('/settings/update-profile', methods=['POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()
    form.current_role_id.choices = [(0, 'Not listed / Other')] + [(role.id, role.title) for role in roles]

    if not form.validate_on_submit():
        flash('Please correct the errors in your profile form.', 'danger')
        return redirect(url_for('profile.settings_page', tab='profile'))

    current_user.first_name = form.first_name.data.strip()
    current_user.current_role_id = None if form.current_role_id.data == 0 else form.current_role_id.data
    current_user.years_experience = form.years_experience.data
    db.session.commit()
    flash('Profile updated successfully.', 'success')
    return redirect(url_for('profile.settings_page', tab='profile'))


@profile_bp.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if not form.validate_on_submit():
        flash('Please check the password fields and try again.', 'danger')
        return redirect(url_for('profile.settings_page', tab='password'))

    if not check_password_hash(current_user.password_hash, form.current_password.data):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile.settings_page', tab='password'))

    current_user.password_hash = generate_password_hash(form.new_password.data)
    db.session.commit()
    flash('Password updated successfully.', 'success')
    return redirect(url_for('profile.settings_page', tab='password'))


@profile_bp.route('/settings/update-notifications', methods=['POST'])
@login_required
def update_notifications():
    form = NotificationPreferencesForm()
    if not form.validate_on_submit():
        flash('Please review your notification preferences.', 'danger')
        return redirect(url_for('profile.settings_page', tab='notifications'))

    prefs = {
        'email_weekly_checkin': bool(form.email_weekly_checkin.data),
        'email_journey_published': bool(form.email_journey_published.data),
        'email_session_updates': bool(form.email_session_updates.data),
        'email_product_updates': bool(form.email_product_updates.data),
        'email_marketing': bool(form.email_marketing.data),
    }
    current_user.notification_preferences = prefs
    db.session.commit()
    flash('Notification preferences updated.', 'success')
    return redirect(url_for('profile.settings_page', tab='notifications'))


@profile_bp.route('/billing')
@login_required
def billing_page():
    action_form = SimpleActionForm()
    payments = (
        SubscriptionPayment.query
        .filter_by(user_id=current_user.id)
        .order_by(SubscriptionPayment.payment_date.desc())
        .limit(24)
        .all()
    )
    total_paid = sum((Decimal(p.amount_inr) for p in payments), Decimal('0.00')) if payments else Decimal('0.00')
    next_renewal_date = current_user.subscription_expires.strftime('%B %d, %Y') if current_user.subscription_expires else None
    tier = current_user.subscription_tier or 'free'
    if not current_user.is_premium:
        current_plan_name = 'Free'
    elif tier == 'annual':
        current_plan_name = 'Premium Annual'
    elif tier == 'admin_granted':
        current_plan_name = 'Premium (Admin Granted)'
    else:
        current_plan_name = 'Premium Monthly'

    return render_template(
        'profile/billing.html',
        payments=payments,
        total_paid_inr=total_paid,
        next_renewal_date=next_renewal_date,
        current_plan_name=current_plan_name,
        razorpay_key_id=current_app.config.get('RAZORPAY_KEY_ID'),
        action_form=action_form,
        title='Billing'
    )


@profile_bp.route('/settings/request-data-export', methods=['POST'])
@login_required
def request_data_export():
    form = SimpleActionForm()
    if not form.validate_on_submit():
        flash('Unable to process export request. Please try again.', 'danger')
        return redirect(url_for('profile.settings_page', tab='privacy'))
    export_payload = {
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'first_name': current_user.first_name,
            'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
            'is_verified': current_user.is_verified,
            'is_premium': current_user.is_premium,
            'subscription_tier': current_user.subscription_tier,
            'subscription_expires': current_user.subscription_expires.isoformat() if current_user.subscription_expires else None,
        },
        'assessments': [
            {
                'id': a.id,
                'created_at': a.created_at.isoformat() if a.created_at else None,
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'is_current': a.is_current,
                'values_data': a.values_data,
                'workstyle_data': a.workstyle_data,
                'skills_data': a.skills_data,
                'constraints_data': a.constraints_data,
                'vision_data': a.vision_data,
                'profile_summary': a.profile_summary,
            }
            for a in UserAssessment.query.filter_by(user_id=current_user.id).all()
        ],
        'analyses': [
            {
                'id': s.id,
                'origin_role_id': s.origin_role_id,
                'target_role_id': s.target_role_id,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'transfer_score': s.transfer_score,
                'gap_score': s.gap_score,
                'feasibility_score': s.feasibility_score,
                'feasibility_breakdown': s.feasibility_breakdown,
                'decision_data': s.decision_data,
            }
            for s in SkillTransferAnalysis.query.filter_by(user_id=current_user.id).all()
        ],
        'roadmaps': [
            {
                'id': r.id,
                'target_role_id': r.target_role_id,
                'analysis_id': r.analysis_id,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'start_date': r.start_date.isoformat() if r.start_date else None,
                'hours_per_week': r.hours_per_week,
                'priority_balance': r.priority_balance,
                'milestones': r.milestones,
                'overall_progress_pct': r.overall_progress_pct,
                'is_active': r.is_active,
            }
            for r in PivotRoadmap.query.filter_by(user_id=current_user.id).all()
        ],
        'progress_entries': [
            {
                'id': p.id,
                'roadmap_id': p.roadmap_id,
                'entry_date': p.entry_date.isoformat() if p.entry_date else None,
                'tasks_completed': p.tasks_completed,
                'reflection': p.reflection,
                'mood_rating': p.mood_rating,
                'obstacles_noted': p.obstacles_noted,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            }
            for p in ProgressEntry.query.filter_by(user_id=current_user.id).all()
        ],
        'journeys': [
            {
                'id': j.id,
                'origin_role_id': j.origin_role_id,
                'target_role_id': j.target_role_id,
                'summary': j.summary,
                'what_worked': j.what_worked,
                'what_failed': j.what_failed,
                'unexpected_discoveries': j.unexpected_discoveries,
                'advice_to_others': j.advice_to_others,
                'is_published': j.is_published,
                'submitted_at': j.submitted_at.isoformat() if j.submitted_at else None,
                'published_at': j.published_at.isoformat() if j.published_at else None,
            }
            for j in Journey.query.filter_by(submitter_user_id=current_user.id).all()
        ],
        'session_bookings': [
            {
                'id': b.id,
                'provider_id': b.provider_id,
                'amount_inr': float(b.amount_inr),
                'status': b.status,
                'booked_at': b.booked_at.isoformat() if b.booked_at else None,
                'session_scheduled_at': b.session_scheduled_at.isoformat() if b.session_scheduled_at else None,
            }
            for b in SessionBooking.query.filter_by(booker_user_id=current_user.id).all()
        ],
        'subscription_payments': [
            {
                'id': sp.id,
                'amount_inr': float(sp.amount_inr),
                'plan_type': sp.plan_type,
                'payment_status': sp.payment_status,
                'payment_date': sp.payment_date.isoformat() if sp.payment_date else None,
                'razorpay_payment_id': sp.razorpay_payment_id,
                'razorpay_subscription_id': sp.razorpay_subscription_id,
            }
            for sp in SubscriptionPayment.query.filter_by(user_id=current_user.id).all()
        ]
    }

    buffer = io.BytesIO()
    buffer.write(json.dumps(export_payload, indent=2, default=str).encode('utf-8'))
    buffer.seek(0)
    filename = f'PathMap_Data_Export_{current_user.id}.json'
    return send_file(buffer, mimetype='application/json', as_attachment=True, download_name=filename)


@profile_bp.route('/settings/request-gdpr-deletion', methods=['POST'])
@login_required
def request_gdpr_deletion():
    form = GDPRDeletionForm()
    if not form.validate_on_submit():
        flash('To confirm deletion, please type DELETE exactly.', 'danger')
        return redirect(url_for('profile.settings_page', tab='privacy'))

    current_user.gdpr_deletion_requested = True
    current_user.gdpr_deletion_requested_at = datetime.utcnow()
    db.session.commit()

    try:
        send_gdpr_deletion_confirmation_email(current_user.email, current_user.first_name or 'PathMapper')
        send_admin_notification(
            subject='GDPR deletion request received',
            body=f'User {current_user.email} (ID {current_user.id}) requested data deletion.'
        )
    except Exception:
        pass

    flash('Your data deletion request has been received. Your account and all associated data will be permanently deleted within 30 days. You will receive a confirmation email when complete.', 'info')
    logout_user()
    return redirect(url_for('main.index'))


@profile_bp.route('/admin/execute-gdpr-deletion/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def execute_gdpr_deletion(user_id):
    user = User.query.get_or_404(user_id)

    try:
        user_email = user.email
        user_name = user.first_name or 'User'

        # Anonymize journeys
        Journey.query.filter_by(submitter_user_id=user.id).update({Journey.submitter_user_id: None})

        # Delete progress entries
        ProgressEntry.query.filter_by(user_id=user.id).delete()

        # Delete roadmaps
        PivotRoadmap.query.filter_by(user_id=user.id).delete()

        # Delete analyses
        SkillTransferAnalysis.query.filter_by(user_id=user.id).delete()

        # Delete assessments
        UserAssessment.query.filter_by(user_id=user.id).delete()

        # Anonymize session reviews (display handled via user record anonymization)

        # Anonymize session bookings (retain for finance)
        SessionBooking.query.filter_by(booker_user_id=user.id).update({SessionBooking.booker_user_id: None})

        # Delete bookmarks
        ResourceBookmark.query.filter_by(user_id=user.id).delete()

        # Delete provider applications
        ProviderApplication.query.filter_by(user_id=user.id).delete()

        # Deactivate provider profile
        provider = ShadowSessionProvider.query.filter_by(user_id=user.id).first()
        if provider:
            provider.is_active = False

        # Delete old subscription payments (older than 7 years)
        cutoff = datetime.utcnow() - timedelta(days=365 * 7)
        SubscriptionPayment.query.filter(
            SubscriptionPayment.user_id == user.id,
            SubscriptionPayment.payment_date < cutoff
        ).delete()

        # Anonymize user record
        user.email = f'deleted_{user.id}@pathmap.deleted'
        user.password_hash = 'DELETED'
        user.first_name = 'Deleted User'
        user.is_verified = False
        user.is_premium = False
        user.subscription_tier = 'free'
        user.subscription_expires = None
        user.razorpay_subscription_id = None
        user.subscription_cancel_requested = False
        user.is_active = False
        user.gdpr_deletion_requested = False
        user.gdpr_deletion_requested_at = None

        db.session.commit()

        try:
            send_gdpr_deletion_confirmation_email(user_email, user_name)
        except Exception:
            pass

        return jsonify({'success': True})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('GDPR deletion failed', exc_info=exc)
        return jsonify({'success': False, 'error': 'Deletion failed'}), 500
