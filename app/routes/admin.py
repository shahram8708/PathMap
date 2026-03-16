from datetime import datetime, timedelta
from collections import defaultdict
import csv
import io

from flask import Blueprint, render_template, abort, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func

from ..extensions import db
from ..forms.profile_forms import (
    BlogPostForm,
    JourneyModerationForm,
    ProviderRejectionForm,
    SimpleActionForm,
)
from ..models.user import User
from ..models.journey import Journey, JourneyView
from ..models.session import ShadowSessionProvider, SessionBooking, ProviderApplication, BlogPost
from ..models.payment import SubscriptionPayment, AdminAuditLog
from ..utils.decorators import admin_required
from ..utils.helpers import log_admin_action


admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    cutoff_30d = datetime.utcnow() - timedelta(days=30)
    cutoff_90d = datetime.utcnow() - timedelta(days=90)

    total_users = User.query.count()
    premium_users = User.query.filter_by(is_premium=True).count()
    active_users_90d = User.query.filter(User.last_active >= cutoff_90d).count()
    pending_gdpr = User.query.filter_by(gdpr_deletion_requested=True).count()

    payments = SubscriptionPayment.query.order_by(SubscriptionPayment.payment_date.desc()).limit(180).all()

    def payment_month(payment):
        dt = payment.payment_date or getattr(payment, 'created_at', None) or datetime.utcnow()
        return dt

    revenue_30d = 0.0
    revenue_trend = defaultdict(float)
    for p in payments:
        dt = payment_month(p)
        amount = float(p.amount_inr or 0)
        if dt >= cutoff_30d:
            revenue_30d += amount
        revenue_trend[dt.strftime('%Y-%m')] += amount
    revenue_series = sorted(revenue_trend.items()) or [(datetime.utcnow().strftime('%Y-%m'), 0.0)]

    bookings = SessionBooking.query.order_by(SessionBooking.booked_at.desc()).limit(180).all()
    bookings_trend = defaultdict(int)
    for b in bookings:
        dt = b.booked_at or getattr(b, 'created_at', None) or datetime.utcnow()
        bookings_trend[dt.strftime('%Y-%m')] += 1
    booking_series = sorted(bookings_trend.items()) or [(datetime.utcnow().strftime('%Y-%m'), 0)]

    published_journeys = Journey.query.filter_by(is_published=True).count()
    unpublished_journeys = Journey.query.filter_by(is_published=False).count()
    provider_count = ShadowSessionProvider.query.filter_by(is_active=True).count()
    pending_applications = ProviderApplication.query.filter_by(application_status='pending').count()

    top_journeys = (
        db.session.query(Journey, func.count(JourneyView.id).label('views'))
        .join(JourneyView, JourneyView.journey_id == Journey.id)
        .group_by(Journey.id)
        .order_by(func.count(JourneyView.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        title='Admin Panel',
        total_users=total_users,
        premium_users=premium_users,
        active_users_90d=active_users_90d,
        pending_gdpr=pending_gdpr,
        revenue_30d=revenue_30d,
        revenue_series=revenue_series,
        booking_series=booking_series,
        published_journeys=published_journeys,
        unpublished_journeys=unpublished_journeys,
        provider_count=provider_count,
        pending_applications=pending_applications,
        top_journeys=top_journeys,
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    action_form = SimpleActionForm()
    users_list = User.query.order_by(User.created_at.desc()).limit(200).all()
    premium_count = sum(1 for u in users_list if u.is_premium)
    inactive_count = sum(1 for u in users_list if not u.is_active)
    return render_template(
        'admin/users.html',
        users=users_list,
        action_form=action_form,
        premium_count=premium_count,
        inactive_count=inactive_count,
        title='Admin • Users'
    )


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(user_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    log_admin_action(current_user.id, 'toggle_user_active', 'User', user.id, f'active={user.is_active}')
    db.session.commit()
    flash(f'User {user.email} active status set to {"active" if user.is_active else "inactive"}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_user_admin(user_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    log_admin_action(current_user.id, 'toggle_admin_flag', 'User', user.id, f'is_admin={user.is_admin}')
    db.session.commit()
    flash(f'User {user.email} admin status updated.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/grant-premium', methods=['POST'])
@login_required
@admin_required
def grant_premium(user_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    user = User.query.get_or_404(user_id)
    user.is_premium = True
    user.subscription_tier = 'admin_granted'
    user.subscription_expires = None
    user.subscription_cancel_requested = False
    log_admin_action(current_user.id, 'grant_premium', 'User', user.id, 'Admin granted premium access')
    db.session.commit()
    flash(f'Premium access granted to {user.email}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/journeys')
@login_required
@admin_required
def journeys_admin():
    moderation_form = JourneyModerationForm()
    action_form = SimpleActionForm()
    journeys = Journey.query.order_by(Journey.submitted_at.desc()).limit(100).all()
    return render_template(
        'admin/journeys.html',
        journeys=journeys,
        moderation_form=moderation_form,
        action_form=action_form,
        title='Admin • Journeys'
    )


@admin_bp.route('/journeys/<int:journey_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_journey(journey_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    journey = Journey.query.get_or_404(journey_id)
    journey.is_published = True
    journey.published_at = datetime.utcnow()
    journey.rejection_reason = None
    log_admin_action(current_user.id, 'publish_journey', 'Journey', journey.id)
    db.session.commit()
    flash('Journey published.', 'success')
    return redirect(url_for('admin.journeys_admin'))


@admin_bp.route('/journeys/<int:journey_id>/unpublish', methods=['POST'])
@login_required
@admin_required
def unpublish_journey(journey_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    journey = Journey.query.get_or_404(journey_id)
    journey.is_published = False
    log_admin_action(current_user.id, 'unpublish_journey', 'Journey', journey.id)
    db.session.commit()
    flash('Journey unpublished.', 'info')
    return redirect(url_for('admin.journeys_admin'))


@admin_bp.route('/journeys/<int:journey_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_journey(journey_id):
    form = JourneyModerationForm()
    if not form.validate_on_submit() or not (form.rejection_reason.data and form.rejection_reason.data.strip()):
        flash('Please include a rejection reason.', 'danger')
        return redirect(url_for('admin.journeys_admin'))
    journey = Journey.query.get_or_404(journey_id)
    journey.is_published = False
    journey.rejection_reason = form.rejection_reason.data.strip()
    log_admin_action(current_user.id, 'reject_journey', 'Journey', journey.id, journey.rejection_reason)
    db.session.commit()
    flash('Journey rejected and saved with feedback.', 'info')
    return redirect(url_for('admin.journeys_admin'))


@admin_bp.route('/providers')
@login_required
@admin_required
def providers_admin():
    action_form = SimpleActionForm()
    rejection_form = ProviderRejectionForm()
    providers = ShadowSessionProvider.query.order_by(ShadowSessionProvider.created_at.desc()).limit(100).all()
    applications = (
        ProviderApplication.query.filter_by(application_status='pending')
        .order_by(ProviderApplication.submitted_at.desc())
        .limit(100)
        .all()
    )
    total_applications = ProviderApplication.query.count()
    return render_template(
        'admin/providers.html',
        providers=providers,
        applications=applications,
        total_applications=total_applications,
        action_form=action_form,
        rejection_form=rejection_form,
        title='Admin • Providers'
    )


@admin_bp.route('/providers/applications/<int:app_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_provider(app_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    application = ProviderApplication.query.get_or_404(app_id)
    application.application_status = 'approved'
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by_admin_id = current_user.id

    existing_provider = ShadowSessionProvider.query.filter_by(user_id=application.user_id).first()
    if not existing_provider:
        provider_profile = ShadowSessionProvider(
            user_id=application.user_id,
            current_role_id=application.current_role_id,
            display_name=application.proposed_display_name,
            bio=application.proposed_bio,
            session_description=application.proposed_session_description,
            session_format='1:1 virtual session',
            price_inr=application.proposed_price_inr,
            booking_url='',
            is_active=True,
            is_verified=True,
            industries_covered=None,
            years_in_target_role=None,
        )
        db.session.add(provider_profile)

    applicant = User.query.get(application.user_id)
    if applicant:
        applicant.is_journey_provider = True

    log_admin_action(current_user.id, 'approve_provider_application', 'ProviderApplication', application.id)
    db.session.commit()
    flash('Provider application approved.', 'success')
    return redirect(url_for('admin.providers_admin'))


@admin_bp.route('/providers/applications/<int:app_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_provider(app_id):
    form = ProviderRejectionForm()
    if not form.validate_on_submit():
        flash('Please include a rejection reason.', 'danger')
        return redirect(url_for('admin.providers_admin'))
    application = ProviderApplication.query.get_or_404(app_id)
    application.application_status = 'rejected'
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by_admin_id = current_user.id
    application.rejection_reason = form.rejection_reason.data.strip()
    log_admin_action(current_user.id, 'reject_provider_application', 'ProviderApplication', application.id, application.rejection_reason)
    db.session.commit()
    flash('Provider application rejected.', 'info')
    return redirect(url_for('admin.providers_admin'))


@admin_bp.route('/sessions')
@login_required
@admin_required
def sessions_admin():
    action_form = SimpleActionForm()
    bookings = SessionBooking.query.order_by(SessionBooking.booked_at.desc()).limit(120).all()
    return render_template('admin/sessions.html', bookings=bookings, action_form=action_form, title='Admin • Sessions')


@admin_bp.route('/sessions/<int:booking_id>/mark-refunded', methods=['POST'])
@login_required
@admin_required
def mark_booking_refunded(booking_id):
    form = SimpleActionForm()
    if not form.validate_on_submit():
        abort(400)
    booking = SessionBooking.query.get_or_404(booking_id)
    booking.status = 'refunded'
    booking.refund_reason = booking.refund_reason or 'Refund processed manually by admin'
    log_admin_action(current_user.id, 'mark_booking_refunded', 'SessionBooking', booking.id)
    db.session.commit()
    flash('Booking marked as refunded.', 'info')
    return redirect(url_for('admin.sessions_admin'))


@admin_bp.route('/blog', methods=['GET', 'POST'])
@login_required
@admin_required
def blog_admin():
    form = BlogPostForm()
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(100).all()

    if form.validate_on_submit():
        slug = form.slug.data.strip() if form.slug.data else form.title.data.lower().replace(' ', '-')[0:280]
        existing = BlogPost.query.filter_by(slug=slug).first()
        if existing:
            flash('Slug already exists. Please pick another.', 'danger')
            return redirect(url_for('admin.blog_admin'))

        post = BlogPost(
            title=form.title.data.strip(),
            slug=slug,
            content=form.content.data,
            excerpt=form.excerpt.data,
            tags=form.tags.data,
            is_published=bool(form.is_published.data),
            published_at=datetime.utcnow() if form.is_published.data else None,
            author_id=current_user.id,
            cover_image_url=form.cover_image_url.data or None,
        )
        db.session.add(post)
        log_admin_action(current_user.id, 'create_blog_post', 'BlogPost', post.id, post.slug)
        db.session.commit()
        flash('Blog post created.', 'success')
        return redirect(url_for('admin.blog_admin'))

    return render_template('admin/blog.html', form=form, posts=posts, title='Admin • Blog')


@admin_bp.route('/gdpr')
@login_required
@admin_required
def gdpr_admin():
    action_form = SimpleActionForm()
    pending_users = User.query.filter_by(gdpr_deletion_requested=True).order_by(User.gdpr_deletion_requested_at.asc()).all()
    return render_template('admin/gdpr.html', pending_users=pending_users, action_form=action_form, title='Admin • GDPR')


@admin_bp.route('/revenue/export')
@login_required
@admin_required
def export_revenue_csv():
    payments = SubscriptionPayment.query.order_by(SubscriptionPayment.payment_date.desc()).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Invoice', 'User ID', 'Plan', 'Amount INR', 'Status', 'Date', 'Payment ID', 'Subscription ID'])
    for p in payments:
        writer.writerow([
            p.invoice_number or f'PM-{p.id}',
            p.user_id,
            p.plan_type,
            float(p.amount_inr or 0),
            p.payment_status,
            p.payment_date.strftime('%Y-%m-%d') if p.payment_date else '',
            p.razorpay_payment_id,
            p.razorpay_subscription_id
        ])
    buffer.seek(0)
    filename = f'pathmap_revenue_export_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    return Response(buffer.getvalue(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})


@admin_bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    entries = AdminAuditLog.query.order_by(AdminAuditLog.performed_at.desc()).limit(200).all()
    return render_template('admin/audit_log.html', entries=entries, title='Admin • Audit Log')
