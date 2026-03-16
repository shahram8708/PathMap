from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
import hmac
import io

import razorpay
from razorpay.errors import BadRequestError
from flask import Blueprint, current_app, jsonify, request, url_for, Response, flash, redirect
from flask_login import login_required, current_user

from ..extensions import db, csrf
from ..models.user import User
from ..models.payment import SubscriptionPayment
from ..services.email_service import (
    send_premium_welcome_email,
    send_subscription_cancelled_email,
    send_payment_failed_email,
)

payment_bp = Blueprint('payment', __name__)


# Important: Before using this payment system, create two plans in your Razorpay Dashboard:
# Monthly Plan at ₹1,499 (interval: monthly) and Annual Plan at ₹11,999 (interval: yearly).
# Copy the generated plan IDs into your .env as RAZORPAY_MONTHLY_PLAN_ID and RAZORPAY_ANNUAL_PLAN_ID.


def _razorpay_client():
    return razorpay.Client(auth=(
        current_app.config.get('RAZORPAY_KEY_ID', ''),
        current_app.config.get('RAZORPAY_KEY_SECRET', '')
    ))


def _plan_price_paise(plan_type: str) -> int:
    default = 149900 if plan_type == 'monthly' else 1199900
    key = 'RAZORPAY_MONTHLY_PRICE_PAISE' if plan_type == 'monthly' else 'RAZORPAY_ANNUAL_PRICE_PAISE'
    try:
        value = int(current_app.config.get(key) or default)
    except (TypeError, ValueError):
        value = default
    # Guard against bad env values (e.g., 1 paise); Razorpay amounts are in paise.
    if value < 100:  # minimum ₹1.00, but we expect ₹1499/₹11999
        current_app.logger.warning('Invalid %s value %s; reverting to default %s', key, value, default)
        value = default
    return value


def _ensure_plan_id(razorpay_client: razorpay.Client, plan_type: str) -> str:
    config_key = 'RAZORPAY_MONTHLY_PLAN_ID' if plan_type == 'monthly' else 'RAZORPAY_ANNUAL_PLAN_ID'
    plan_id = current_app.config.get(config_key)
    target_amount = _plan_price_paise(plan_type)

    if plan_id and 'placeholder' not in str(plan_id):
        try:
            existing_plan = razorpay_client.plan.fetch(plan_id)
            existing_amount = int(((existing_plan or {}).get('item') or {}).get('amount') or 0)
            if existing_amount == target_amount:
                return plan_id
            current_app.logger.warning(
                'Razorpay plan %s amount %s does not match expected %s — creating a new plan',
                plan_id, existing_amount, target_amount
            )
        except Exception as exc:
            current_app.logger.warning('Unable to fetch Razorpay plan %s; creating a new one', plan_id, exc_info=exc)

    plan_name = 'PathMap Premium Monthly' if plan_type == 'monthly' else 'PathMap Premium Annual'
    period = 'monthly' if plan_type == 'monthly' else 'yearly'
    plan = razorpay_client.plan.create({
        'period': period,
        'interval': 1,
        'item': {
            'name': plan_name,
            'amount': target_amount,
            'currency': 'INR',
            'description': 'PathMap subscription'
        }
    })
    plan_id = plan['id']
    current_app.config[config_key] = plan_id
    return plan_id


def _infer_plan_type(plan_id=None, subscription=None, payment_amount_paise=None, notes=None) -> str:
    monthly_plan_id = current_app.config.get('RAZORPAY_MONTHLY_PLAN_ID')
    annual_plan_id = current_app.config.get('RAZORPAY_ANNUAL_PLAN_ID')
    if plan_id and plan_id == monthly_plan_id:
        return 'monthly'
    if plan_id and plan_id == annual_plan_id:
        return 'annual'

    notes = notes or {}
    if notes.get('plan_type') in {'monthly', 'annual'}:
        return notes['plan_type']

    plan_obj = subscription.get('plan') if subscription else None
    plan_item = (plan_obj or {}).get('item') or {}
    amount_paise = plan_item.get('amount')
    if amount_paise is None and subscription:
        amount_paise = subscription.get('plan_amount')
    if amount_paise is None and payment_amount_paise is not None:
        amount_paise = payment_amount_paise

    monthly_price = _plan_price_paise('monthly')
    annual_price = _plan_price_paise('annual')
    try:
        amount_val = int(amount_paise)
        if abs(amount_val - annual_price) < abs(amount_val - monthly_price):
            return 'annual'
    except (TypeError, ValueError):
        pass
    return 'monthly'


@payment_bp.route('/create-subscription', methods=['POST'])
@login_required
def create_subscription():
    data = request.get_json(silent=True) or {}
    plan_type = data.get('plan_type')

    if plan_type not in {'monthly', 'annual'}:
        return jsonify({'success': False, 'error': 'Invalid plan selected.'}), 400

    if current_user.is_premium:
        return jsonify({'success': False, 'error': 'You already have an active Premium subscription.'}), 400

    key_id = current_app.config.get('RAZORPAY_KEY_ID')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET')
    if not key_id or not key_secret:
        return jsonify({'success': False, 'error': 'Payments are temporarily unavailable. Please contact support@pathmap.in.'}), 503

    razorpay_client = _razorpay_client()
    try:
        plan_id = _ensure_plan_id(razorpay_client, plan_type)
    except Exception as exc:
        current_app.logger.error('Unable to prepare Razorpay plan for %s', plan_type, exc_info=exc)
        return jsonify({'success': False, 'error': 'Payment setup is unavailable right now. Please try again shortly.'}), 500

    total_count = 120 if plan_type == 'monthly' else 10

    try:
        subscription = razorpay_client.subscription.create({
            'plan_id': plan_id,
            'total_count': total_count,
            'quantity': 1,
            'customer_notify': 1,
            'notes': {
                'user_id': str(current_user.id),
                'user_email': current_user.email,
                'plan_type': plan_type
            }
        })
        current_user.razorpay_subscription_id = subscription['id']
        current_user.subscription_cancel_requested = False
        db.session.commit()
        return jsonify({
            'success': True,
            'subscription_id': subscription['id'],
            'key': current_app.config.get('RAZORPAY_KEY_ID'),
            'plan_type': plan_type,
            'user_email': current_user.email,
            'user_name': current_user.first_name or ''
        })
    except Exception as exc:  # razorpay API errors are subclasses of Exception
        current_app.logger.error('Unable to create subscription via Razorpay', exc_info=exc)
        return jsonify({
            'success': False,
            'error': 'Unable to create subscription. Please try again or contact support@pathmap.in.'
        }), 500


@payment_bp.route('/verify-subscription', methods=['POST'])
@login_required
def verify_subscription():
    data = request.get_json(silent=True) or {}
    payment_id = data.get('razorpay_payment_id')
    subscription_id = data.get('razorpay_subscription_id')
    signature = data.get('razorpay_signature')

    if not payment_id or not subscription_id or not signature:
        return jsonify({'success': False, 'error': 'Missing payment verification details.'}), 400

    if current_user.razorpay_subscription_id != subscription_id:
        return jsonify({'success': False, 'error': 'Subscription mismatch. Please try again.'}), 400

    razorpay_client = _razorpay_client()
    try:
        expected = hmac.new(
            current_app.config.get('RAZORPAY_KEY_SECRET', '').encode(),
            f"{payment_id}|{subscription_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return jsonify({'success': False, 'error': 'Payment verification failed. Please contact support@pathmap.in.'}), 400
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'success': False, 'error': 'Payment verification failed. Please contact support@pathmap.in.'}), 400

    try:
        subscription = razorpay_client.subscription.fetch(subscription_id)
        subscription_tier = _infer_plan_type(
            plan_id=subscription.get('plan_id'),
            subscription=subscription,
            notes=subscription.get('notes') or {}
        )
        extension_days = 31 if subscription_tier == 'monthly' else 366
        subscription_expires = datetime.utcnow() + timedelta(days=extension_days)

        current_user.is_premium = True
        current_user.subscription_tier = subscription_tier
        current_user.subscription_expires = subscription_expires
        current_user.razorpay_subscription_id = subscription_id
        current_user.subscription_cancel_requested = False
        db.session.commit()

        try:
            send_premium_welcome_email(current_user, subscription_tier, subscription_expires)
        except Exception as exc:
            current_app.logger.error('Failed sending premium welcome email', exc_info=exc)

        return jsonify({
            'success': True,
            'redirect_url': url_for('dashboard.main_dashboard'),
            'message': 'Welcome to PathMap Premium! All features are now unlocked.'
        })
    except Exception as exc:  # catch Razorpay API errors or db issues
        current_app.logger.error('Subscription verification error', exc_info=exc)
        return jsonify({'success': False, 'error': 'Payment verification failed. Please contact support@pathmap.in.'}), 400


@payment_bp.route('/webhook', methods=['POST'])
@csrf.exempt
def razorpay_webhook():
    raw_body = request.get_data()
    signature = request.headers.get('X-Razorpay-Signature', '') or ''
    expected = hmac.new(
        current_app.config.get('RAZORPAY_WEBHOOK_SECRET', '').encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        current_app.logger.warning('Razorpay webhook signature mismatch from IP %s', request.remote_addr)
        return Response('Unauthorized', status=400)

    event_data = request.get_json(silent=True) or {}
    event = event_data.get('event')

    try:
        if event == 'subscription.activated':
            subscription_id = event_data['payload']['subscription']['entity']['id']
            notes = event_data['payload']['subscription']['entity'].get('notes', {})
            user_id = notes.get('user_id')
            user = User.query.get(int(user_id)) if user_id else None
            if user:
                subscription_entity = event_data['payload']['subscription']['entity']
                plan_type = _infer_plan_type(
                    plan_id=subscription_entity.get('plan_id'),
                    subscription=subscription_entity,
                    notes=subscription_entity.get('notes') or {}
                )
                user.subscription_tier = plan_type
                user.is_premium = True
                user.razorpay_subscription_id = subscription_id
                user.subscription_cancel_requested = False
                db.session.commit()
                current_app.logger.info('Subscription activated for user %s', user.email)

        elif event == 'subscription.charged':
            subscription_entity = event_data['payload']['subscription']['entity']
            payment_entity = event_data['payload']['payment']['entity']
            subscription_id = subscription_entity['id']
            payment_id = payment_entity['id']
            amount_paise = Decimal(payment_entity.get('amount', 0))
            amount_inr = (amount_paise / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            existing = SubscriptionPayment.query.filter_by(razorpay_payment_id=payment_id).first()
            if existing:
                return Response('OK', status=200)

            user = User.query.filter_by(razorpay_subscription_id=subscription_id).first()
            if user:
                plan_type = _infer_plan_type(
                    plan_id=subscription_entity.get('plan_id'),
                    subscription=subscription_entity,
                    payment_amount_paise=int(payment_entity.get('amount') or 0),
                    notes=subscription_entity.get('notes') or {}
                )
                extension_days = 31 if plan_type == 'monthly' else 366
                user.subscription_expires = datetime.utcnow() + timedelta(days=extension_days)

                payment_record = SubscriptionPayment(
                    user_id=user.id,
                    razorpay_payment_id=payment_id,
                    razorpay_subscription_id=subscription_id,
                    amount_inr=amount_inr,
                    plan_type=plan_type,
                    payment_status='captured',
                    payment_date=datetime.utcnow()
                )
                db.session.add(payment_record)
                db.session.commit()
                current_app.logger.info('Subscription charge recorded for user %s', user.email)

        elif event == 'subscription.cancelled':
            subscription_id = event_data['payload']['subscription']['entity']['id']
            user = User.query.filter_by(razorpay_subscription_id=subscription_id).first()
            if user:
                user.razorpay_subscription_id = None
                user.subscription_cancel_requested = True
                db.session.commit()
                try:
                    send_subscription_cancelled_email(user, user.subscription_expires)
                except Exception as exc:
                    current_app.logger.error('Failed sending cancellation email', exc_info=exc)
                current_app.logger.info('Subscription cancelled for user %s', user.email)

        elif event == 'subscription.completed':
            subscription_id = event_data['payload']['subscription']['entity']['id']
            user = User.query.filter_by(razorpay_subscription_id=subscription_id).first()
            if user:
                user.razorpay_subscription_id = None
                user.subscription_cancel_requested = True
                db.session.commit()
                try:
                    send_subscription_cancelled_email(user, user.subscription_expires)
                except Exception as exc:
                    current_app.logger.error('Failed sending completion email', exc_info=exc)

        elif event == 'payment.failed':
            payment_entity = event_data['payload']['payment']['entity']
            subscription_id = payment_entity.get('subscription_id')
            failure_reason = payment_entity.get('error_description') or payment_entity.get('error_reason', 'Unknown reason')
            user = User.query.filter_by(razorpay_subscription_id=subscription_id).first()
            if user:
                try:
                    send_payment_failed_email(user)
                except Exception as exc:
                    current_app.logger.error('Failed sending payment failure email', exc_info=exc)
                current_app.logger.warning('Payment failed for user %s: %s', user.email, failure_reason)

    except Exception as exc:
        current_app.logger.error('Error handling Razorpay webhook', exc_info=exc)
        return Response('OK', status=200)

    return Response('OK', status=200)


@payment_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    if not current_user.is_premium or not current_user.razorpay_subscription_id:
        flash('You do not have an active subscription to cancel.', 'warning')
        return redirect(url_for('profile.billing_page'))

    razorpay_client = _razorpay_client()
    try:
        razorpay_client.subscription.cancel(current_user.razorpay_subscription_id, {'cancel_at_cycle_end': 1})
        current_user.subscription_cancel_requested = True
        db.session.commit()
        expiry_text = current_user.subscription_expires.strftime('%B %d, %Y') if current_user.subscription_expires else 'the end of this cycle'
        flash(f'Your subscription has been cancelled. You will retain Premium access until {expiry_text}. No further charges will be made.', 'info')
        try:
            send_subscription_cancelled_email(current_user, current_user.subscription_expires)
        except Exception as exc:
            current_app.logger.error('Failed sending cancellation confirmation', exc_info=exc)
    except Exception as exc:
        current_app.logger.error('Error cancelling Razorpay subscription', exc_info=exc)
        flash('We could not cancel your subscription at this time. Please try again or contact support@pathmap.in.', 'danger')
    return redirect(url_for('profile.billing_page'))


@payment_bp.route('/reactivate-subscription', methods=['POST'])
@login_required
def reactivate_subscription():
    if not current_user.is_premium or not current_user.subscription_cancel_requested:
        flash('No cancelled subscription found to reactivate.', 'warning')
        return redirect(url_for('profile.billing_page'))

    razorpay_client = _razorpay_client()
    try:
        razorpay_client.subscription.resume(current_user.razorpay_subscription_id, {'resume_at': 'now'})
    except BadRequestError as exc:
        message = (str(exc) or '').lower()
        if 'active state' in message:
            current_app.logger.info('Subscription already active in Razorpay for user %s; clearing cancel flag.', current_user.email)
            current_user.subscription_cancel_requested = False
            db.session.commit()
            flash('Your subscription is already active. Premium access continues.', 'info')
            return redirect(url_for('profile.billing_page'))
        current_app.logger.error('Error reactivating subscription', exc_info=exc)
        flash('We could not reactivate your subscription. Please try again or contact support@pathmap.in.', 'danger')
        return redirect(url_for('profile.billing_page'))
    except Exception as exc:
        current_app.logger.error('Error reactivating subscription', exc_info=exc)
        flash('We could not reactivate your subscription. Please try again or contact support@pathmap.in.', 'danger')
        return redirect(url_for('profile.billing_page'))

    current_user.subscription_cancel_requested = False
    db.session.commit()
    flash('Your subscription has been reactivated. Premium access will continue without interruption.', 'success')
    return redirect(url_for('profile.billing_page'))


@payment_bp.route('/download-invoices', methods=['GET'])
@login_required
def download_invoices():
    payments = (
        SubscriptionPayment.query
        .filter_by(user_id=current_user.id)
        .order_by(SubscriptionPayment.payment_date.desc())
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Invoice', 'Plan', 'Amount INR', 'Status', 'Date', 'Payment ID'])
    for p in payments:
        writer.writerow([
            p.invoice_number or f'PM-{p.id}',
            p.plan_type,
            float(p.amount_inr or 0),
            p.payment_status,
            p.payment_date.strftime('%Y-%m-%d') if p.payment_date else '',
            p.razorpay_payment_id
        ])
    buffer.seek(0)
    filename = f'pathmap_invoices_user_{current_user.id}.csv'
    return Response(
        buffer.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
