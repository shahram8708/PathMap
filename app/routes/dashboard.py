from datetime import date, datetime
from flask import Blueprint, render_template, jsonify, request, session, url_for
from flask_login import login_required, current_user
from ..models.assessment import UserAssessment
from ..models.roadmap import PivotRoadmap, ProgressEntry
from ..models.analysis import SkillTransferAnalysis
from ..services import ai_service


dashboard_bp = Blueprint('dashboard', __name__)


def _compute_streak(entries):
    streak = 0
    today = date.today()
    prev_date = today
    for entry in entries:
        if (prev_date - entry.entry_date).days <= 7:
            streak += 1
            prev_date = entry.entry_date
        else:
            break
    return streak


def get_next_assessment_url():
    assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).first()
    if not assessment or not assessment.values_completed:
        return url_for('assessment.values_module')
    elif not assessment.workstyle_completed:
        return url_for('assessment.workstyle_module')
    elif not assessment.skills_completed:
        return url_for('assessment.skills_module')
    elif not assessment.constraints_completed:
        return url_for('assessment.constraints_module')
    elif not assessment.vision_completed:
        return url_for('assessment.vision_module')
    else:
        return url_for('assessment.assessment_results')


@dashboard_bp.route('/')
@login_required
def main_dashboard():
    assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).first()
    if assessment:
        completed_count = assessment.completed_modules_count
        assessment_percentage = (completed_count / 5) * 100
        assessment_progress = {
            'values': assessment.values_completed,
            'workstyle': assessment.workstyle_completed,
            'skills': assessment.skills_completed,
            'constraints': assessment.constraints_completed,
            'vision': assessment.vision_completed,
            'completed_count': completed_count,
            'percentage': assessment_percentage
        }
    else:
        assessment_progress = {
            'values': False,
            'workstyle': False,
            'skills': False,
            'constraints': False,
            'vision': False,
            'completed_count': 0,
            'percentage': 0
        }

    active_roadmap = (
        PivotRoadmap.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(PivotRoadmap.created_at.desc())
        .first()
    )

    current_week = None
    current_week_tasks = None
    days_into_pivot = None
    overall_progress_pct = None
    if active_roadmap:
        today = date.today()
        if active_roadmap.start_date > today:
            current_week = 0
        else:
            delta_days = (today - active_roadmap.start_date).days
            days_into_pivot = min(delta_days, 90)
            current_week = min((delta_days // 7) + 1, 13)
        milestones = active_roadmap.milestones or []
        week_index = max(current_week - 1, 0) if current_week is not None else 0
        if milestones and 0 <= week_index < len(milestones):
            current_week_tasks = milestones[week_index].get('tasks', []) if isinstance(milestones[week_index], dict) else None
        if days_into_pivot is None and active_roadmap.start_date <= today:
            days_into_pivot = min((today - active_roadmap.start_date).days, 90)

        entries_for_roadmap = ProgressEntry.query.filter_by(roadmap_id=active_roadmap.id).all()
        completed_tasks_count = sum(len(entry.tasks_completed or []) for entry in entries_for_roadmap)
        total_tasks = active_roadmap.estimated_total_tasks
        if total_tasks and total_tasks > 0:
            overall_progress_pct = min(int((completed_tasks_count / total_tasks) * 100), 100)
        else:
            overall_progress_pct = 0

    entries = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(ProgressEntry.entry_date.desc())
        .all()
    )
    streak_count = _compute_streak(entries)
    total_checkins = len(entries)
    last_checkin_days_ago = None
    if entries:
        last_checkin_days_ago = (date.today() - entries[0].entry_date).days

    saved_analyses_count = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .count()
    )

    journeys_available = bool(current_user.is_premium)

    greeting_hour = datetime.now().hour
    if 5 <= greeting_hour <= 11:
        greeting_time = 'morning'
    elif 12 <= greeting_hour <= 17:
        greeting_time = 'afternoon'
    elif 18 <= greeting_hour <= 21:
        greeting_time = 'evening'
    else:
        greeting_time = 'night'

    cached_date = session.get('dashboard_message_date')
    cached_text = session.get('dashboard_message_text')
    today_str = date.today().isoformat()
    if cached_date == today_str and cached_text:
        ai_welcome_message = cached_text
    else:
        ai_welcome_message = ai_service.get_dashboard_welcome(current_user, assessment)
        session['dashboard_message_date'] = today_str
        session['dashboard_message_text'] = ai_welcome_message

    days_since_joining = 0
    if current_user.created_at:
        days_since_joining = (date.today() - current_user.created_at.date()).days

    quick_actions = []
    if not assessment or assessment_progress['percentage'] < 100:
        quick_actions.append({
            'icon': 'bi-clipboard-check',
            'label': 'Complete Your Assessment',
            'url': url_for('assessment.assessment_hub'),
            'color': 'accent',
            'priority': 1
        })
    if assessment and assessment_progress['percentage'] >= 100 and saved_analyses_count == 0:
        quick_actions.append({
            'icon': 'bi-diagram-3',
            'label': 'Run Your First Skill Analysis',
            'url': url_for('analysis.new_analysis'),
            'color': 'navy',
            'priority': 2
        })
    if saved_analyses_count > 0 and not active_roadmap:
        quick_actions.append({
            'icon': 'bi-map',
            'label': 'Build Your 90-Day Roadmap',
            'url': url_for('planner.roadmap_form'),
            'color': 'success',
            'priority': 3
        })
    if active_roadmap and last_checkin_days_ago is not None and last_checkin_days_ago > 6:
        quick_actions.append({
            'icon': 'bi-check2-square',
            'label': "Log This Week's Progress",
            'url': url_for('progress.checkin_form'),
            'color': 'warning',
            'priority': 1
        })
    quick_actions.append({
        'icon': 'bi-journal-richtext',
        'label': 'Explore Career Journeys',
        'url': url_for('journeys.explorer'),
        'color': 'purple',
        'priority': 4
    })
    quick_actions = sorted(quick_actions, key=lambda x: x['priority'])[:4]

    return render_template(
        'dashboard/dashboard.html',
        user=current_user,
        assessment=assessment,
        assessment_progress=assessment_progress,
        active_roadmap=active_roadmap,
        roadmap_current_week=current_week,
        current_week_tasks=current_week_tasks,
        streak_count=streak_count,
        total_checkins=total_checkins,
        saved_analyses_count=saved_analyses_count,
        journeys_available=journeys_available,
        days_into_pivot=days_into_pivot,
        overall_progress_pct=overall_progress_pct,
        last_checkin_days_ago=last_checkin_days_ago,
        ai_welcome_message=ai_welcome_message,
        quick_actions=quick_actions,
        greeting_time=greeting_time,
        next_assessment_url=get_next_assessment_url(),
        days_since_joining=days_since_joining
    )


@dashboard_bp.route('/ai-insight', methods=['POST'])
@login_required
def ai_insight_ajax():
    data = request.get_json(silent=True) or {}
    question = (data.get('question') or '').strip()
    if not question or len(question) > 500:
        return jsonify({'answer': 'Please enter a concise question (max 500 characters).', 'success': False}), 400

    if not current_user.is_premium:
        today_str = date.today().isoformat()
        usage = session.get('ai_insight_usage', {}) or {}
        used_today = usage.get(today_str, 0)
        if used_today >= 3:
            return jsonify({
                'success': False,
                'error': "You've used your 3 free AI questions today. Upgrade to Premium for unlimited AI insights (₹1,499/month).",
                'limit_reached': True
            }), 429

    latest_assessment = (
        UserAssessment.query
        .filter_by(user_id=current_user.id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    context = {
        'current_role_id': current_user.current_role_id,
        'years_experience': current_user.years_experience,
        'pivot_motivation': current_user.pivot_motivation,
        'assessment_complete': bool(latest_assessment and latest_assessment.is_fully_complete),
        'top_values': (latest_assessment.profile_summary or {}).get('top_values') if latest_assessment and latest_assessment.profile_summary else None,
    }
    try:
        answer = ai_service.get_ai_career_insight(question, context)
        if not current_user.is_premium:
            today_str = date.today().isoformat()
            usage = session.get('ai_insight_usage', {}) or {}
            usage[today_str] = usage.get(today_str, 0) + 1
            session['ai_insight_usage'] = usage
        return jsonify({'answer': answer, 'success': True})
    except Exception:
        return jsonify({'answer': "I'm unable to answer right now. Please try again shortly.", 'success': False}), 500
