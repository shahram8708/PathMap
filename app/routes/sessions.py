from datetime import datetime
from decimal import Decimal

import razorpay
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_mail import Message
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import joinedload

from ..extensions import db, mail
from ..forms.session_forms import (
    BookingForm,
    ProviderApplicationForm,
    ProviderEditForm,
    SessionReviewForm
)
from ..models.role import Role
from ..models.session import (
    ProviderApplication,
    SessionBooking,
    SessionReview,
    ShadowSessionProvider
)
from ..utils.decorators import premium_required


sessions_bp = Blueprint('sessions', __name__)


@sessions_bp.route('/', methods=['GET'], endpoint='marketplace')
@login_required
def marketplace():
    page = request.args.get('page', 1, type=int)
    role_id = request.args.get('role_id', type=int)
    industry = request.args.get('industry', type=str)
    price_min = request.args.get('price_min', type=int)
    price_max = request.args.get('price_max', type=int)
    min_rating = request.args.get('min_rating', type=float)
    sort_by = request.args.get('sort_by', default='rating', type=str)
    search_term = request.args.get('search', type=str)

    provider_query = ShadowSessionProvider.query.filter(
        ShadowSessionProvider.is_active.is_(True),
        ShadowSessionProvider.is_verified.is_(True)
    ).join(Role)

    if role_id:
        provider_query = provider_query.filter(ShadowSessionProvider.current_role_id == role_id)

    if industry:
        provider_query = provider_query.filter(ShadowSessionProvider.industries_covered.ilike(f"%{industry}%"))

    if price_min is not None:
        provider_query = provider_query.filter(ShadowSessionProvider.price_inr >= price_min)

    if price_max is not None:
        provider_query = provider_query.filter(ShadowSessionProvider.price_inr <= price_max)

    if min_rating is not None:
        provider_query = provider_query.filter(ShadowSessionProvider.avg_rating >= Decimal(str(min_rating)))

    if search_term:
        like_term = f"%{search_term}%"
        provider_query = provider_query.filter(
            or_(
                ShadowSessionProvider.display_name.ilike(like_term),
                Role.title.ilike(like_term)
            )
        )

    sort_map = {
        'rating': ShadowSessionProvider.avg_rating.desc(),
        'price_low': ShadowSessionProvider.price_inr.asc(),
        'price_high': ShadowSessionProvider.price_inr.desc(),
        'most_sessions': ShadowSessionProvider.total_sessions.desc(),
        'newest': ShadowSessionProvider.created_at.desc()
    }
    provider_query = provider_query.order_by(sort_map.get(sort_by, ShadowSessionProvider.avg_rating.desc()))

    pagination = provider_query.paginate(page=page, per_page=12, error_out=False)
    providers = pagination.items

    industries_raw = (
        db.session.query(ShadowSessionProvider.industries_covered)
        .filter(ShadowSessionProvider.is_active.is_(True), ShadowSessionProvider.is_verified.is_(True))
        .all()
    )
    filter_industries = set()
    for row in industries_raw:
        if row and row[0]:
            for part in row[0].split(','):
                part_clean = part.strip()
                if part_clean:
                    filter_industries.add(part_clean)
    filter_industries = sorted(filter_industries)

    filter_roles = (
        Role.query
        .join(ShadowSessionProvider, ShadowSessionProvider.current_role_id == Role.id)
        .filter(Role.is_active.is_(True), ShadowSessionProvider.is_active.is_(True))
        .group_by(Role.id)
        .order_by(Role.title.asc())
        .all()
    )

    price_ranges = [
        ('0', '2000', 'Under ₹2,000'),
        ('2000', '4000', '₹2,000 – ₹4,000'),
        ('4000', '6000', '₹4,000 – ₹6,000'),
        ('6000', '999999', 'Above ₹6,000')
    ]

    total_providers = provider_query.count()
    avg_price = db.session.query(func.avg(ShadowSessionProvider.price_inr)).filter(
        ShadowSessionProvider.is_active.is_(True), ShadowSessionProvider.is_verified.is_(True)
    ).scalar() or 0
    total_sessions_completed = db.session.query(func.sum(ShadowSessionProvider.total_sessions)).scalar() or 0

    marketplace_stats = {
        'total_providers': total_providers,
        'avg_price': float(avg_price) if avg_price else 0,
        'avg_price_display': f"{float(avg_price):,.0f}" if avg_price else '0',
        'total_sessions_completed': int(total_sessions_completed)
    }

    current_filters = {
        'role_id': role_id,
        'industry': industry,
        'price_min': price_min,
        'price_max': price_max,
        'min_rating': min_rating,
        'sort_by': sort_by,
        'search': search_term
    }

    return render_template(
        'sessions/marketplace.html',
        providers=providers,
        pagination=pagination,
        filter_industries=filter_industries,
        filter_roles=filter_roles,
        price_ranges=price_ranges,
        marketplace_stats=marketplace_stats,
        current_filters=current_filters,
        is_premium=current_user.is_premium
    )


@sessions_bp.route('/<int:provider_id>', methods=['GET'], endpoint='provider_profile')
@login_required
def provider_profile(provider_id: int):
    provider = ShadowSessionProvider.query.options(joinedload(ShadowSessionProvider.current_role)).get(provider_id)
    if not provider or not provider.is_active or not provider.is_verified:
        abort(404)

    reviews = (
        SessionReview.query
        .options(joinedload(SessionReview.reviewer))
        .filter_by(provider_id=provider_id, is_published=True)
        .order_by(desc(SessionReview.created_at))
        .limit(10)
        .all()
    )
    completed_sessions = SessionBooking.query.filter_by(provider_id=provider_id, status='session_completed').count()
    existing_booking = SessionBooking.query.filter_by(provider_id=provider_id, booker_user_id=current_user.id).first()
    is_own_profile = provider.user_id == current_user.id

    rating_distribution = {i: 0 for i in range(1, 6)}
    distribution_rows = (
        db.session.query(SessionReview.rating, func.count(SessionReview.id))
        .filter(SessionReview.provider_id == provider_id, SessionReview.is_published.is_(True))
        .group_by(SessionReview.rating)
        .all()
    )
    for rating, count in distribution_rows:
        rating_distribution[int(rating)] = count

    booking_form = BookingForm()

    return render_template(
        'sessions/provider_profile.html',
        provider=provider,
        reviews=reviews,
        completed_sessions=completed_sessions,
        existing_booking=existing_booking,
        is_own_profile=is_own_profile,
        rating_distribution=rating_distribution,
        is_premium=current_user.is_premium,
        booking_form=booking_form
    )


@sessions_bp.route('/book/<int:provider_id>', methods=['GET'], endpoint='book_session')
@login_required
@premium_required
def book_session(provider_id: int):
    provider = ShadowSessionProvider.query.options(joinedload(ShadowSessionProvider.current_role)).get(provider_id)
    if not provider or not provider.is_active or not provider.is_verified:
        abort(404)

    if provider.user_id == current_user.id:
        flash('You cannot book your own session.', 'danger')
        return redirect(url_for('sessions.marketplace'))

    existing_active = SessionBooking.query.filter(
        SessionBooking.provider_id == provider_id,
        SessionBooking.booker_user_id == current_user.id,
        SessionBooking.status.in_(['pending', 'paid', 'session_scheduled'])
    ).first()
    if existing_active:
        flash('You already have an active booking with this provider.', 'info')
        return redirect(url_for('sessions.my_bookings'))

    amount_inr = Decimal(str(provider.price_inr))
    commission_inr, provider_payout_inr = SessionBooking.compute_commission(amount_inr)

    form = BookingForm()

    return render_template(
        'sessions/book.html',
        provider=provider,
        amount_inr=amount_inr,
        commission_inr=commission_inr,
        provider_payout_inr=provider_payout_inr,
        razorpay_key_id=current_app.config.get('RAZORPAY_KEY_ID', ''),
        form=form
    )


@sessions_bp.route('/book/<int:provider_id>/create-order', methods=['POST'], endpoint='create_booking_order')
@login_required
@premium_required
def create_booking_order(provider_id: int):
    provider = ShadowSessionProvider.query.get(provider_id)
    if not provider or not provider.is_active or not provider.is_verified:
        return jsonify({'success': False, 'error': 'Provider not available.'}), 404

    data = request.get_json(silent=True) or {}
    notes_from_booker = data.get('notes_from_booker')

    try:
        amount_decimal = Decimal(str(provider.price_inr))
        commission_inr, provider_payout_inr = SessionBooking.compute_commission(amount_decimal)

        razorpay_client = razorpay.Client(auth=(
            current_app.config['RAZORPAY_KEY_ID'],
            current_app.config['RAZORPAY_KEY_SECRET']
        ))

        amount_paise = int(amount_decimal * 100)
        order_data = razorpay_client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'notes': {
                'provider_id': str(provider_id),
                'provider_name': provider.display_name,
                'booker_user_id': str(current_user.id),
                'type': 'shadow_session_booking'
            }
        })

        booking = SessionBooking(
            provider_id=provider_id,
            booker_user_id=current_user.id,
            amount_inr=amount_decimal,
            commission_inr=commission_inr,
            provider_payout_inr=provider_payout_inr,
            razorpay_order_id=order_data['id'],
            status='pending',
            notes_from_booker=notes_from_booker
        )
        db.session.add(booking)
        db.session.commit()

        return jsonify({
            'success': True,
            'order_id': order_data['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'key': current_app.config['RAZORPAY_KEY_ID'],
            'booking_id': booking.id,
            'provider_name': provider.display_name,
            'description': f"Shadow Session with {provider.display_name} — {provider.current_role.title}"
        })
    except Exception as exc:  # pragma: no cover - unexpected runtime errors
        current_app.logger.error(f'Failed to create Razorpay order: {exc}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@sessions_bp.route('/book/<int:provider_id>/verify-payment', methods=['POST'], endpoint='verify_booking_payment')
@login_required
def verify_booking_payment(provider_id: int):
    data = request.get_json(silent=True) or {}
    payment_id = data.get('razorpay_payment_id')
    order_id = data.get('razorpay_order_id')
    signature = data.get('razorpay_signature')
    booking_id = data.get('booking_id')

    booking = SessionBooking.query.get_or_404(booking_id)
    if booking.booker_user_id != current_user.id:
        abort(403)

    if booking.status == 'paid':
        return jsonify({
            'success': True,
            'message': 'Payment already verified.',
            'redirect_url': url_for('sessions.booking_confirmation', booking_id=booking.id)
        })

    provider = ShadowSessionProvider.query.get_or_404(provider_id)

    try:
        razorpay_client = razorpay.Client(auth=(
            current_app.config['RAZORPAY_KEY_ID'],
            current_app.config['RAZORPAY_KEY_SECRET']
        ))

        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })

        booking.status = 'paid'
        booking.razorpay_payment_id = payment_id
        booking.razorpay_signature = signature
        booking.payment_captured_at = datetime.utcnow()
        provider.total_sessions = (provider.total_sessions or 0) + 1
        db.session.commit()

        _send_booking_emails(booking, provider)

        return jsonify({
            'success': True,
            'message': 'Payment verified. Your session is confirmed!',
            'redirect_url': url_for('sessions.booking_confirmation', booking_id=booking.id)
        })
    except razorpay.errors.SignatureVerificationError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Payment verification failed. Please contact support@pathmap.in with your order ID.'
        }), 400
    except Exception as exc:  # pragma: no cover - unexpected runtime errors
        db.session.rollback()
        current_app.logger.error(f'Unexpected error verifying payment for booking {booking_id}: {exc}')
        return jsonify({'success': False, 'error': 'An error occurred while verifying payment.'}), 500


@sessions_bp.route('/booking/<int:booking_id>/confirmation', methods=['GET'], endpoint='booking_confirmation')
@login_required
def booking_confirmation(booking_id: int):
    booking = SessionBooking.query.options(joinedload(SessionBooking.provider)).get_or_404(booking_id)
    if booking.booker_user_id != current_user.id:
        abort(403)
    if booking.status == 'pending':
        flash('Payment is still pending. Please complete your booking.', 'warning')
        return redirect(url_for('sessions.marketplace'))

    provider = booking.provider
    return render_template('sessions/booking_confirmation.html', booking=booking, provider=provider)


@sessions_bp.route('/my-bookings', methods=['GET'], endpoint='my_bookings')
@login_required
def my_bookings():
    bookings = (
        SessionBooking.query.options(joinedload(SessionBooking.provider).joinedload(ShadowSessionProvider.current_role))
        .filter_by(booker_user_id=current_user.id)
        .order_by(desc(SessionBooking.booked_at))
        .all()
    )

    active_bookings = [b for b in bookings if b.status in ['paid', 'session_scheduled']]
    completed_bookings = [b for b in bookings if b.status == 'session_completed']
    pending_bookings = [b for b in bookings if b.status == 'pending']

    provider_profile = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first()
    provider_recent_bookings = []
    if provider_profile:
        provider_recent_bookings = (
            SessionBooking.query
            .filter_by(provider_id=provider_profile.id)
            .order_by(desc(SessionBooking.booked_at))
            .limit(5)
            .all()
        )

    return render_template(
        'sessions/my_bookings.html',
        bookings=bookings,
        active_bookings=active_bookings,
        completed_bookings=completed_bookings,
        pending_bookings=pending_bookings,
        provider_profile=provider_profile,
        provider_recent_bookings=provider_recent_bookings
    )


@sessions_bp.route('/book/<int:booking_id>/review', methods=['GET'], endpoint='leave_review_form')
@login_required
def leave_review_form(booking_id: int):
    booking = SessionBooking.query.get_or_404(booking_id)
    if booking.booker_user_id != current_user.id:
        abort(403)
    if not booking.can_be_reviewed:
        flash('This booking is not eligible for review yet.', 'warning')
        return redirect(url_for('sessions.provider_profile', provider_id=booking.provider_id))
    if booking.has_review:
        flash('You have already reviewed this session.', 'info')
        return redirect(url_for('sessions.provider_profile', provider_id=booking.provider_id))

    form = SessionReviewForm()
    provider = ShadowSessionProvider.query.get_or_404(booking.provider_id)
    return render_template('sessions/leave_review.html', form=form, booking=booking, provider=provider)


@sessions_bp.route('/book/<int:booking_id>/review', methods=['POST'], endpoint='submit_review')
@login_required
def submit_review(booking_id: int):
    form = SessionReviewForm()
    booking = SessionBooking.query.get_or_404(booking_id)
    provider = ShadowSessionProvider.query.get_or_404(booking.provider_id)

    if booking.booker_user_id != current_user.id:
        abort(403)
    if not booking.can_be_reviewed:
        flash('This booking cannot be reviewed yet.', 'warning')
        return redirect(url_for('sessions.provider_profile', provider_id=provider.id))
    if provider.user_id == current_user.id:
        abort(403)

    if form.validate_on_submit():
        review = SessionReview(
            provider_id=provider.id,
            reviewer_user_id=current_user.id,
            booking_id=booking.id,
            rating=form.rating.data,
            review_text=form.review_text.data,
            would_recommend=form.would_recommend.data,
            session_helped_decision=form.session_helped_decision.data,
            is_verified=True,
            is_published=True
        )
        booking.has_review = True
        db.session.add(review)
        db.session.commit()

        avg_rating = db.session.query(func.avg(SessionReview.rating)).filter(
            SessionReview.provider_id == provider.id,
            SessionReview.is_published.is_(True)
        ).scalar() or 0
        provider.avg_rating = Decimal(str(avg_rating)).quantize(Decimal('0.01')) if avg_rating else Decimal('0.00')
        provider.total_reviews = (provider.total_reviews or 0) + 1
        db.session.commit()

        flash('Thank you for leaving a review!', 'success')
        return redirect(url_for('sessions.provider_profile', provider_id=provider.id))

    return render_template('sessions/leave_review.html', form=form, booking=booking, provider=provider)


@sessions_bp.route('/become-provider', methods=['GET'], endpoint='become_provider')
@login_required
def become_provider():
    existing_profile = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('You already have a provider profile.', 'info')
        return redirect(url_for('sessions.provider_dashboard'))

    pending_application = ProviderApplication.query.filter_by(user_id=current_user.id, application_status='pending').first()
    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()

    if pending_application:
        return render_template('sessions/become_provider.html', form=None, pending_application=pending_application, roles=roles)

    form = ProviderApplicationForm()
    form.current_role_id.choices = [(r.id, r.title) for r in roles]
    return render_template('sessions/become_provider.html', form=form, pending_application=None, roles=roles)


@sessions_bp.route('/become-provider', methods=['POST'], endpoint='submit_provider_application')
@login_required
def submit_provider_application():
    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()
    form = ProviderApplicationForm()
    form.current_role_id.choices = [(r.id, r.title) for r in roles]

    existing_profile = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first()
    pending_application = ProviderApplication.query.filter_by(user_id=current_user.id, application_status='pending').first()
    if existing_profile:
        flash('You already have a provider profile.', 'info')
        return redirect(url_for('sessions.provider_dashboard'))
    if pending_application:
        flash('Your application is already under review.', 'info')
        return redirect(url_for('sessions.become_provider'))

    if form.validate_on_submit():
        application = ProviderApplication(
            user_id=current_user.id,
            current_role_id=form.current_role_id.data,
            proposed_display_name=form.proposed_display_name.data,
            proposed_bio=form.proposed_bio.data,
            proposed_session_description=form.proposed_session_description.data,
            proposed_price_inr=form.proposed_price_inr.data,
            why_good_provider=form.why_good_provider.data,
            linkedin_url=form.linkedin_url.data,
            rejection_reason=None
        )
        db.session.add(application)
        db.session.commit()

        _send_provider_application_email(application)

        flash("Your application has been submitted! We review applications within 3 business days. You'll receive an email with our decision.", 'success')
        return redirect(url_for('sessions.marketplace'))

    return render_template('sessions/become_provider.html', form=form, pending_application=None, roles=roles)


@sessions_bp.route('/provider/dashboard', methods=['GET'], endpoint='provider_dashboard')
@login_required
def provider_dashboard():
    provider = ShadowSessionProvider.query.options(joinedload(ShadowSessionProvider.current_role)).filter_by(user_id=current_user.id).first()
    if not provider:
        return redirect(url_for('sessions.become_provider'))

    bookings = (
        SessionBooking.query
        .options(joinedload(SessionBooking.booker))
        .filter_by(provider_id=provider.id)
        .order_by(desc(SessionBooking.booked_at))
        .all()
    )
    reviews = SessionReview.query.filter_by(provider_id=provider.id).order_by(desc(SessionReview.created_at)).all()

    total_earned = sum([float(b.provider_payout_inr) for b in bookings if b.status == 'session_completed'])
    pending_sessions = len([b for b in bookings if b.status in ['paid', 'session_scheduled']])
    current_month = datetime.utcnow().month
    this_month_earnings = sum([
        float(b.provider_payout_inr)
        for b in bookings
        if b.status == 'session_completed' and b.booked_at.month == current_month
    ])

    earnings_stats = {
        'total_earned': total_earned,
        'pending_sessions': pending_sessions,
        'this_month_earnings': this_month_earnings
    }

    return render_template(
        'sessions/provider_dashboard.html',
        provider=provider,
        bookings=bookings,
        reviews=reviews,
        earnings_stats=earnings_stats
    )


@sessions_bp.route('/provider/edit', methods=['GET'], endpoint='edit_provider_profile')
@login_required
def edit_provider_profile():
    provider = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first()
    if not provider:
        return redirect(url_for('sessions.become_provider'))

    form = ProviderEditForm()
    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()
    form.current_role_id.choices = [(r.id, r.title) for r in roles]

    # Pre-fill with the provider's saved data so the edit form reflects current values
    form.current_role_id.data = provider.current_role_id
    form.proposed_display_name.data = provider.display_name
    form.proposed_bio.data = provider.bio
    form.proposed_session_description.data = provider.session_description
    form.session_format.data = provider.session_format
    form.proposed_price_inr.data = int(provider.price_inr) if provider.price_inr is not None else None
    form.industries_covered.data = provider.industries_covered
    form.years_in_target_role.data = provider.years_in_target_role
    form.booking_url.data = provider.booking_url
    form.transition_story.data = provider.transition_story
    form.is_active.data = provider.is_active
    return render_template('sessions/edit_provider.html', form=form, provider=provider, roles=roles)


@sessions_bp.route('/provider/edit', methods=['POST'], endpoint='save_provider_profile')
@login_required
def save_provider_profile():
    provider = ShadowSessionProvider.query.filter_by(user_id=current_user.id).first_or_404()
    roles = Role.query.filter_by(is_active=True).order_by(Role.title.asc()).all()
    form = ProviderEditForm()
    form.current_role_id.choices = [(r.id, r.title) for r in roles]

    if form.validate_on_submit():
        provider.current_role_id = form.current_role_id.data
        provider.display_name = form.proposed_display_name.data
        provider.bio = form.proposed_bio.data
        provider.session_description = form.proposed_session_description.data
        provider.price_inr = form.proposed_price_inr.data
        provider.industries_covered = form.industries_covered.data
        provider.years_in_target_role = form.years_in_target_role.data
        provider.booking_url = form.booking_url.data
        provider.session_format = form.session_format.data
        provider.transition_story = form.transition_story.data
        provider.is_active = form.is_active.data
        db.session.commit()
        flash('Your provider profile has been updated.', 'success')
        return redirect(url_for('sessions.provider_dashboard'))

    return render_template('sessions/edit_provider.html', form=form, provider=provider, roles=roles)


@sessions_bp.route('/booking/<int:booking_id>/mark-complete', methods=['POST'], endpoint='mark_session_complete')
@login_required
def mark_session_complete(booking_id: int):
    booking = SessionBooking.query.get_or_404(booking_id)
    if booking.booker_user_id != current_user.id and booking.provider.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    if booking.status not in ['session_scheduled', 'paid']:
        return jsonify({'success': False, 'error': 'This session cannot be marked complete.'}), 400

    booking.status = 'session_completed'
    booking.session_completed_at = datetime.utcnow()
    db.session.commit()

    _send_review_invitation_email(booking)

    return jsonify({'success': True, 'message': 'Session marked as complete. Please leave a review.'})


@sessions_bp.route('/booking/<int:booking_id>/schedule', methods=['POST'], endpoint='schedule_session')
@login_required
def schedule_session(booking_id: int):
    booking = SessionBooking.query.options(
        joinedload(SessionBooking.booker),
        joinedload(SessionBooking.provider)
    ).get_or_404(booking_id)

    if booking.provider.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Not authorized to schedule this session.'}), 403

    if booking.status not in ['paid', 'session_scheduled']:
        return jsonify({'success': False, 'error': 'Booking must be paid before scheduling.'}), 400

    payload = request.get_json(silent=True) or request.form or {}
    scheduled_at_raw = payload.get('scheduled_at')
    session_link = (payload.get('session_link') or '').strip()

    if not scheduled_at_raw or not session_link:
        return jsonify({'success': False, 'error': 'Schedule time and join link are required.'}), 400

    try:
        scheduled_at = datetime.fromisoformat(str(scheduled_at_raw))
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date/time format.'}), 400

    if not session_link.lower().startswith(('http://', 'https://')):
        session_link = f"https://{session_link}"

    booking.session_scheduled_at = scheduled_at
    booking.session_link = session_link
    booking.status = 'session_scheduled'
    db.session.commit()

    _send_session_schedule_email(booking)

    return jsonify({'success': True, 'scheduled_at': scheduled_at.isoformat()})


def _send_booking_emails(booking: SessionBooking, provider: ShadowSessionProvider) -> None:
    try:
        booker_msg = Message(
            subject=f"Your PathMap Shadow Session is Confirmed — Booking #{booking.id}",
            recipients=[booking.booker.email],
            html=render_template('emails/session_booking_confirmation_booker.html', booking=booking, provider=provider)
        )
        provider_msg = Message(
            subject=f"New Session Booking — ₹{float(booking.provider_payout_inr):,.0f} for Your Shadow Session",
            recipients=[provider.user.email],
            html=render_template('emails/session_booking_confirmation_provider.html', booking=booking, provider=provider)
        )
        mail.send(booker_msg)
        mail.send(provider_msg)
    except Exception as exc:  # pragma: no cover - email failures should not block flow
        current_app.logger.error(f'Failed to send booking confirmation email for booking {booking.id}: {exc}')


def _send_review_invitation_email(booking: SessionBooking) -> None:
    try:
        provider = ShadowSessionProvider.query.get(booking.provider_id)
        msg = Message(
            subject=f"How was your PathMap shadow session? Leave a review for {provider.display_name}",
            recipients=[booking.booker.email],
            html=render_template('emails/session_review_invitation.html', booking=booking, provider=provider)
        )
        mail.send(msg)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f'Failed to send review invitation for booking {booking.id}: {exc}')


def _send_session_schedule_email(booking: SessionBooking) -> None:
    booker_email = booking.booker.email if booking.booker else None
    if not booker_email:
        current_app.logger.error(f'Cannot send schedule email for booking {booking.id}: missing booker email')
        return

    try:
        provider = booking.provider
        msg = Message(
            subject=f"Your PathMap session with {provider.display_name} is scheduled",
            recipients=[booker_email],
            html=render_template('emails/session_schedule_confirmation.html', booking=booking, provider=provider)
        )
        mail.send(msg)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f'Failed to send schedule email for booking {booking.id}: {exc}')


def _send_provider_application_email(application: ProviderApplication) -> None:
    admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@pathmap.in')
    try:
        admin_msg = Message(
            subject='New PathMap Provider Application',
            recipients=[admin_email],
            body=(
                f"New provider application submitted by user {application.user_id}\n"
                f"Display name: {application.proposed_display_name}\n"
                f"Price: ₹{float(application.proposed_price_inr):,.0f}"
            )
        )
        applicant_msg = Message(
            subject='Your PathMap Provider Application is Under Review',
            recipients=[application.user.email],
            html=render_template('emails/provider_application_received.html', application=application)
        )
        mail.send(admin_msg)
        mail.send(applicant_msg)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f'Failed to send provider application emails for application {application.id}: {exc}')