import re
from datetime import datetime, timedelta
from flask import request
from ..extensions import db
from ..models.assessment import UserAssessment
from ..models.roadmap import ProgressEntry
from ..models.payment import AdminAuditLog


def format_inr(amount):
    """Format a numeric amount into Indian Rupees with proper digit grouping."""
    if amount is None:
        return "₹0"
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return "₹0"
    sign = '-' if value < 0 else ''
    value = abs(int(round(value)))
    digits = str(value)
    if len(digits) <= 3:
        grouped = digits
    else:
        last_three = digits[-3:]
        rest = digits[:-3]
        pairs = []
        while len(rest) > 2:
            pairs.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            pairs.insert(0, rest)
        grouped = ','.join(pairs + [last_three])
    return f"{sign}₹{grouped}"


def time_ago(dt):
    if not dt:
        return "just now"
    now = datetime.utcnow()
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = months // 12
    return f"{years} year{'s' if years != 1 else ''} ago"


def generate_slug(title: str, model_class=None):
    base = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:280]
    slug = base or 'post'
    if not model_class or not getattr(model_class, 'query', None) or not hasattr(model_class, 'slug'):
        return slug
    counter = 2
    while model_class.query.filter_by(slug=slug).first():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def get_assessment_completion_for_user(user_id: int):
    assessment = (
        UserAssessment.query
        .filter_by(user_id=user_id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    if not assessment:
        return {
            'values_completed': False,
            'workstyle_completed': False,
            'skills_completed': False,
            'constraints_completed': False,
            'vision_completed': False,
            'percentage': 0
        }
    return {
        'values_completed': assessment.values_completed,
        'workstyle_completed': assessment.workstyle_completed,
        'skills_completed': assessment.skills_completed,
        'constraints_completed': assessment.constraints_completed,
        'vision_completed': assessment.vision_completed,
        'percentage': assessment.completion_percentage
    }


def compute_streak_count(user_id: int) -> int:
    entries = (
        ProgressEntry.query
        .filter_by(user_id=user_id)
        .order_by(ProgressEntry.entry_date.desc())
        .all()
    )
    if not entries:
        return 0
    streak = 0
    today = datetime.utcnow().date()
    last_date = entries[0].entry_date
    if (today - last_date).days > 7:
        return 0
    streak = 1
    for entry in entries[1:]:
        gap = (last_date - entry.entry_date).days
        if gap <= 7:
            streak += 1
            last_date = entry.entry_date
        else:
            break
    return streak


def truncate_text(text: str, length: int = 150):
    if not text:
        return ''
    if len(text) <= length:
        return text
    cutoff = text[:length]
    if ' ' in cutoff:
        cutoff = cutoff.rsplit(' ', 1)[0]
    return cutoff.strip() + '...'


def log_admin_action(admin_user_id: int, action_type: str, target_type: str = None, target_id: int = None, details=None):
    entry = AdminAuditLog(
        admin_user_id=admin_user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=request.remote_addr
    )
    db.session.add(entry)
    db.session.flush()
    return entry
