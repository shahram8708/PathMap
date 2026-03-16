from datetime import datetime
from functools import wraps
from flask import redirect, url_for, flash, abort, request
from flask_login import current_user
from ..extensions import db
from ..models.assessment import UserAssessment
from ..models.analysis import SkillTransferAnalysis


def premium_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.subscription_expires and current_user.subscription_expires < datetime.utcnow():
            current_user.is_premium = False
            db.session.commit()
        if not current_user.is_premium:
            flash(
                'This feature is available on PathMap Premium (₹1,499/month). Upgrade to access the Decision Framework, 90-Day Roadmap, and full analysis tools.',
                'warning'
            )
            return redirect(url_for('main.pricing'))
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def assessment_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        assessment = (
            UserAssessment.query
            .filter_by(user_id=current_user.id, is_current=True)
            .order_by(UserAssessment.created_at.desc())
            .first()
        )
        if not assessment or not assessment.is_fully_complete:
            flash(
                'Please complete your Career Clarity Assessment before accessing this tool. Your assessment results power this feature.',
                'info'
            )
            return redirect(url_for('assessment.assessment_hub'))
        return func(*args, **kwargs)

    return wrapper


def analysis_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        saved_count = SkillTransferAnalysis.query.filter_by(user_id=current_user.id, is_saved=True).count()
        if saved_count == 0:
            flash(
                'Please complete at least one Skill Transfer Analysis before accessing the Pivot Planner. Your analysis results are required to generate your feasibility score and roadmap.',
                'info'
            )
            return redirect(url_for('analysis.analysis_hub'))
        return func(*args, **kwargs)

    return wrapper
