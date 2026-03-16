from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import current_user, login_required
from flask_mail import Message
from ..extensions import db, mail
from ..forms.progress_forms import JourneySubmissionForm
from ..models.journey import Journey, JourneyView
from ..models.role import Role
from ..services import journey_query


journeys_bp = Blueprint('journeys', __name__)


@journeys_bp.route('/', methods=['GET'], endpoint='explorer')
@login_required
def explorer():
    page = max(int(request.args.get('page', 1)), 1)
    pagination_args = request.args.to_dict()
    pagination_args.pop('page', None)
    filters = {
        'from_role_id': int(request.args.get('from_role_id')) if request.args.get('from_role_id') else None,
        'to_role_id': int(request.args.get('to_role_id')) if request.args.get('to_role_id') else None,
        'outcome': request.args.get('outcome', 'all'),
        'region': request.args.get('region') or None,
        'experience_min': int(request.args.get('experience_min')) if request.args.get('experience_min') else None,
        'experience_max': int(request.args.get('experience_max')) if request.args.get('experience_max') else None,
        'timeline_max': int(request.args.get('timeline_max')) if request.args.get('timeline_max') else None,
        'sort_by': request.args.get('sort_by') or 'recent'
    }

    journeys_paginated, aggregate_stats = journey_query.search_journeys(filters, page=page, per_page=10)
    global_stats = journey_query.get_journey_aggregate_stats_global()

    all_roles = Role.query.filter_by(is_active=True).order_by(Role.title).all()
    region_rows = db.session.query(Journey.geographic_region).filter_by(is_published=True).distinct().all()
    all_regions = [r[0] for r in region_rows if r[0]]

    views_remaining = None
    viewed_ids = set()
    if current_user.is_authenticated and not current_user.is_premium:
        today = date.today()
        user_views = JourneyView.query.filter_by(
            user_id=current_user.id,
            view_month=today.month,
            view_year=today.year
        ).all()
        views_remaining = max(0, 5 - len(user_views))
        viewed_ids = {v.journey_id for v in user_views}

    return render_template(
        'journeys/explorer.html',
        journeys=journeys_paginated.items,
        pagination=journeys_paginated,
        aggregate_stats=aggregate_stats,
        global_stats=global_stats,
        all_roles=all_roles,
        all_regions=all_regions,
        active_filters=filters,
        views_remaining=views_remaining,
        viewed_ids=viewed_ids,
        is_premium=(current_user.is_authenticated and current_user.is_premium),
        pagination_args=pagination_args
    )


@journeys_bp.route('/<int:journey_id>', methods=['GET'], endpoint='journey_detail')
@login_required
def journey_detail(journey_id):
    journey = Journey.query.filter_by(id=journey_id, is_published=True).first()
    if not journey:
        abort(404)

    today = date.today()
    existing_view = JourneyView.query.filter_by(
        user_id=current_user.id,
        journey_id=journey.id,
        view_month=today.month,
        view_year=today.year
    ).first()

    if not current_user.is_premium:
        monthly_views = JourneyView.query.filter_by(
            user_id=current_user.id,
            view_month=today.month,
            view_year=today.year
        ).count()
        if monthly_views >= 5 and not existing_view:
            flash('You have used all 5 free journey views this month. Upgrade to Premium for unlimited access to all journeys.', 'warning')
            return redirect(url_for('main.pricing'))

    if not existing_view:
        journey_query.record_journey_view(current_user.id, journey.id)
    elif current_user.is_premium:
        journey.view_count = (journey.view_count or 0) + 1
        db.session.commit()

    related_journeys = journey_query.get_related_journeys(journey, limit=3)
    transition_stats = journey_query.get_journey_stats_for_transition(journey.origin_role_id, journey.target_role_id)
    income_direction = 'positive' if (journey.income_change_pct or 0) > 5 else 'negative' if (journey.income_change_pct or 0) < -5 else 'neutral'

    return render_template(
        'journeys/detail.html',
        journey=journey,
        origin_role=journey.origin_role,
        target_role=journey.target_role,
        related_journeys=related_journeys,
        income_direction=income_direction,
        transition_stats=transition_stats
    )


@journeys_bp.route('/submit', methods=['GET'], endpoint='submit_journey_form')
@login_required
def submit_journey_form():
    all_roles = Role.query.filter_by(is_active=True).order_by(Role.title).all()
    form = JourneySubmissionForm()
    form.origin_role_id.choices = [(r.id, r.title) for r in all_roles]
    form.target_role_id.choices = [(r.id, r.title) for r in all_roles]

    pending = Journey.query.filter_by(submitter_user_id=current_user.id, is_published=False).first()
    has_pending = pending is not None

    return render_template(
        'journeys/submit.html',
        form=form,
        all_roles=all_roles,
        has_pending=has_pending
    )


@journeys_bp.route('/submit', methods=['POST'], endpoint='submit_journey_save')
@login_required
def submit_journey_save():
    all_roles = Role.query.filter_by(is_active=True).order_by(Role.title).all()
    form = JourneySubmissionForm()
    form.origin_role_id.choices = [(r.id, r.title) for r in all_roles]
    form.target_role_id.choices = [(r.id, r.title) for r in all_roles]

    if not form.validate_on_submit():
        flash('Please fix the errors and resubmit your journey.', 'danger')
        pending = Journey.query.filter_by(submitter_user_id=current_user.id, is_published=False).first()
        return render_template(
            'journeys/submit.html',
            form=form,
            all_roles=all_roles,
            has_pending=bool(pending)
        )

    if not form.submitter_consented.data:
        flash('You must consent to submission to share your journey.', 'danger')
        pending = Journey.query.filter_by(submitter_user_id=current_user.id, is_published=False).first()
        return render_template(
            'journeys/submit.html',
            form=form,
            all_roles=all_roles,
            has_pending=bool(pending)
        )

    journey = Journey(
        submitter_user_id=current_user.id,
        origin_role_id=form.origin_role_id.data,
        target_role_id=form.target_role_id.data,
        origin_industry=form.origin_industry.data,
        target_industry=form.target_industry.data,
        experience_at_pivot=form.experience_at_pivot.data,
        timeline_months=form.timeline_months.data,
        preparation_months=form.preparation_months.data,
        income_change_pct=form.income_change_pct.data,
        outcome_status=form.outcome_status.data,
        reversal_reason=form.reversal_reason.data if form.outcome_status.data == 'reversed' else None,
        summary=form.summary.data,
        what_worked=form.what_worked.data,
        what_failed=form.what_failed.data,
        unexpected_discoveries=form.unexpected_discoveries.data,
        advice_to_others=form.advice_to_others.data,
        total_cost_inr=form.total_cost_inr.data,
        geographic_region=form.geographic_region.data,
        pseudonym=form.pseudonym.data,
        is_published=False,
        submitter_consented=True,
        submitted_at=datetime.utcnow()
    )
    db.session.add(journey)
    db.session.commit()

    try:
        recipient = current_app.config.get('ADMIN_ALERT_EMAIL') or current_app.config.get('MAIL_DEFAULT_SENDER')
        if recipient:
            msg = Message(
                subject='New Journey Submission — PathMap',
                recipients=[recipient],
                body=(
                    f"Origin role: {journey.origin_role.title if journey.origin_role else journey.origin_role_id}\n"
                    f"Target role: {journey.target_role.title if journey.target_role else journey.target_role_id}\n"
                    f"Outcome: {journey.outcome_status}\n"
                    f"Pseudonym: {journey.pseudonym or 'Anonymous'}\n"
                    f"Review URL: {url_for('admin.journeys_admin', _external=True)}"
                )
            )
            mail.send(msg)
    except Exception:
        current_app.logger.warning('Unable to send admin notification for journey submission.', exc_info=True)

    flash('Thank you for submitting your journey! Our team will review it within 3-5 business days. You will be notified by email when it is published.', 'success')
    return redirect(url_for('journeys.explorer'))
