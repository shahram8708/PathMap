from datetime import date, timedelta
from flask_login import current_user

from app.models.assessment import UserAssessment
from app.models.roadmap import ProgressEntry
from app.models.user import User
from app.models.session import ProviderApplication
from app.models.journey import Journey


def inject_assessment_progress():
    if current_user.is_authenticated:
        assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).first()
        if assessment:
            return {'current_assessment_progress': assessment.completed_modules_count}
        return {'current_assessment_progress': 0}
    return {}


def inject_progress_streak():
    if not current_user.is_authenticated:
        return {'current_streak': 0}

    entries = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(ProgressEntry.entry_date.desc())
        .limit(20)
        .all()
    )
    if not entries:
        return {'current_streak': 0}

    weeks_with_entries = {(_isoweek(e.entry_date)) for e in entries}
    today_week = _isoweek(date.today())
    prev_week = _isoweek(date.today() - timedelta(days=7))
    start_week = today_week if today_week in weeks_with_entries else prev_week if prev_week in weeks_with_entries else None
    if not start_week:
        return {'current_streak': 0}

    streak = 0
    anchor = _week_monday(start_week)
    while True:
        key = _isoweek(anchor)
        if key in weeks_with_entries:
            streak += 1
            anchor -= timedelta(days=7)
        else:
            break
    return {'current_streak': streak}


def _isoweek(d):
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _week_monday(week_tuple):
    year, week = week_tuple
    return date.fromisocalendar(year, week, 1)


def inject_admin_badges():
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        return {}
    try:
        pending_gdpr = User.query.filter_by(gdpr_deletion_requested=True).count()
        pending_provider_apps = ProviderApplication.query.filter_by(application_status='pending').count()
        pending_journeys = Journey.query.filter_by(is_published=False).count()
        return {
            'admin_pending_gdpr': pending_gdpr,
            'admin_pending_providers': pending_provider_apps,
            'admin_pending_provider_apps': pending_provider_apps,
            'admin_pending_journeys': pending_journeys,
        }
    except Exception:
        return {}
