import csv
from datetime import date, datetime, timedelta
from io import StringIO
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, abort
from flask_login import login_required, current_user
from ..extensions import db
from ..forms.progress_forms import CheckInForm
from ..models.roadmap import PivotRoadmap, ProgressEntry
from ..services import ai_service

progress_bp = Blueprint('progress', __name__)

WEEKLY_REFLECTION_PROMPTS = [
    "You've completed your first week. What surprised you about getting started? What felt easier or harder than expected?",
    "What specific skill progress did you make this week? Name one thing you learned that you didn't know before.",
    "Have you started reaching out to professionals in your target field? What's your plan for the first informational interview?",
    "First monthly checkpoint! What have you accomplished in Month 1? What needs to change in Month 2?",
    "Are you still confident in your target career direction? What have you learned about the day-to-day reality of that role?",
    "Halfway through your first 2 months. Are you on pace with your hours commitment? Be honest — is your plan realistic?",
    "What is your biggest obstacle right now? Be specific. What is one concrete action you will take to address it this week?",
    "Two-month checkpoint! What progress are you most proud of? What gap remains largest?",
    "Have you done any portfolio work yet? If not, what is stopping you?",
    "You are 70 days in. What does your current skills confidence feel like compared to Day 1?",
    "Are you starting to feel ready to apply for roles? What would need to be true before you feel ready?",
    "One week to go. What is the single most important task to complete in your final week?",
    "90-day retrospective! You made it. What did you accomplish? What is your next 90-day commitment?"
]


def _week_tuple_from_date(d: date):
    iso = d.isocalendar()
    return iso[0], iso[1]


def calculate_streak(entries):
    if not entries:
        return 0
    weeks_with_entries = {_week_tuple_from_date(entry.entry_date) for entry in entries}
    today = date.today()
    current_week = _week_tuple_from_date(today)
    prev_week = _week_tuple_from_date(today - timedelta(days=7))

    start_week = current_week if current_week in weeks_with_entries else prev_week if prev_week in weeks_with_entries else None
    if not start_week:
        return 0

    streak = 0
    anchor = date.fromisocalendar(start_week[0], start_week[1], 1)
    while True:
        key = _week_tuple_from_date(anchor)
        if key in weeks_with_entries:
            streak += 1
            anchor -= timedelta(days=7)
        else:
            break
    return streak


def _longest_weekly_streak(entries):
    if not entries:
        return 0
    weeks = sorted({_week_tuple_from_date(e.entry_date) for e in entries}, reverse=True)
    if not weeks:
        return 0
    longest = current = 1
    for i in range(1, len(weeks)):
        year, wk = weeks[i-1]
        prev_anchor = date.fromisocalendar(year, wk, 1)
        expected = _week_tuple_from_date(prev_anchor - timedelta(days=7))
        if weeks[i] == expected:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def build_heatmap_data(entries):
    start_day = date.today() - timedelta(days=363)
    levels = {}
    for offset in range(364):
        day = start_day + timedelta(days=offset)
        levels[day.isoformat()] = 0

    for entry in entries:
        level = 2
        if entry.mood_rating is not None:
            if entry.mood_rating <= 2:
                level = 1
            elif entry.mood_rating == 3:
                level = 2
            else:
                level = 3
        key = entry.entry_date.isoformat()
        if key in levels:
            levels[key] = max(levels[key], level)
    return levels


def build_mood_chart_data(entries):
    if not entries:
        return {'dates': [], 'moods': []}
    latest = entries[:12]
    ordered = list(reversed(latest))
    dates = [e.entry_date.strftime('%b %d') for e in ordered]
    moods = [e.mood_rating if e.mood_rating is not None else 3 for e in ordered]
    return {'dates': dates, 'moods': moods}


def _compute_week_number(roadmap: PivotRoadmap, entry_date: date) -> int:
    if not roadmap or not roadmap.start_date:
        return 1
    delta_days = max((entry_date - roadmap.start_date).days, 0)
    return min((delta_days // 7) + 1, 13)


def _collect_completed_task_ids(roadmap_id: int, user_id: int):
    entries = ProgressEntry.query.filter_by(roadmap_id=roadmap_id, user_id=user_id).all()
    completed = set()
    for item in entries:
        if item.tasks_completed:
            completed.update(str(t) for t in item.tasks_completed)
    return completed


def _task_lookup_from_milestones(milestones):
    lookup = {}
    for week in milestones or []:
        for task in week.get('tasks', []):
            task_id = str(task.get('id'))
            lookup[task_id] = task.get('title') or task.get('name') or f"Task {task_id}"
    return lookup


@progress_bp.route('/', methods=['GET'], endpoint='progress_dashboard')
@login_required
def progress_dashboard():
    active_roadmap = (
        PivotRoadmap.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(PivotRoadmap.created_at.desc())
        .first()
    )

    all_entries = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(ProgressEntry.entry_date.desc())
        .all()
    )
    recent_entries = all_entries[:5]
    total_entries_count = len(all_entries)
    streak_count = calculate_streak(all_entries)
    heatmap_data = build_heatmap_data(all_entries)
    mood_chart_data = build_mood_chart_data(all_entries)

    reflection_entries = [e for e in recent_entries if e.reflection and e.reflection.strip()][:3]
    last_entry = all_entries[0] if all_entries else None
    days_since = (date.today() - last_entry.entry_date).days if last_entry else None

    current_week_number = None
    current_week_tasks = []
    current_week_completed = []
    week_start_date = None
    week_end_date = None
    upcoming_checkpoint = None
    days_to_checkpoint = None
    overall_progress_pct = 0
    completed_task_ids = set()
    days_into_pivot = None
    weeks_remaining = None

    if active_roadmap:
        delta_days = (date.today() - active_roadmap.start_date).days
        days_into_pivot = max(delta_days, 0)
        current_week_number = 1 if delta_days < 0 else min((delta_days // 7) + 1, 13)
        weeks_remaining = max(0, 13 - current_week_number)
        milestones = active_roadmap.milestones or []
        week_index = max(current_week_number - 1, 0)
        if 0 <= week_index < len(milestones):
            current_week_tasks = milestones[week_index].get('tasks', [])
        completed_task_ids = _collect_completed_task_ids(active_roadmap.id, current_user.id)
        current_week_completed = [t for t in current_week_tasks if str(t.get('id')) in completed_task_ids]
        total_tasks = sum(len(week.get('tasks', [])) for week in milestones)
        overall_progress_pct = round((len(completed_task_ids) / total_tasks) * 100, 2) if total_tasks else 0
        active_roadmap.overall_progress_pct = overall_progress_pct

        start_of_week = active_roadmap.start_date + timedelta(days=(current_week_number - 1) * 7)
        week_start_date = start_of_week
        week_end_date = start_of_week + timedelta(days=6)

        for checkpoint_day in [30, 60, 90]:
            if 0 <= (checkpoint_day - days_into_pivot) <= 7:
                upcoming_checkpoint = checkpoint_day
                days_to_checkpoint = checkpoint_day - days_into_pivot
                break

    checked_in_this_week = False
    if current_week_number is not None:
        start_of_week = date.today() - timedelta(days=date.today().weekday())
        end_of_week = start_of_week + timedelta(days=6)
        checked_in_this_week = any(start_of_week <= e.entry_date <= end_of_week for e in recent_entries)

    return render_template(
        'progress/dashboard.html',
        active_roadmap=active_roadmap,
        all_entries=all_entries,
        recent_entries=recent_entries,
        total_entries_count=total_entries_count,
        streak_count=streak_count,
        heatmap_data=heatmap_data,
        mood_chart_data=mood_chart_data,
        reflection_entries=reflection_entries,
        days_since_last=days_since,
        current_week_number=current_week_number,
        current_week_tasks=current_week_tasks,
        current_week_completed=current_week_completed,
        week_start_date=week_start_date,
        week_end_date=week_end_date,
        upcoming_checkpoint=upcoming_checkpoint,
        days_to_checkpoint=days_to_checkpoint,
        overall_progress_pct=overall_progress_pct,
        completed_task_ids=completed_task_ids,
        days_into_pivot=days_into_pivot,
        weeks_remaining=weeks_remaining,
        checked_in_this_week=checked_in_this_week
    )


@progress_bp.route('/check-in', methods=['GET'], endpoint='checkin_form')
@login_required
def checkin_form():
    active_roadmap = (
        PivotRoadmap.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(PivotRoadmap.created_at.desc())
        .first()
    )
    if not active_roadmap:
        flash('You need an active 90-Day Roadmap before logging check-ins. Generate your roadmap first.', 'info')
        return redirect(url_for('planner.roadmap_form'))

    today = date.today()
    existing_entry = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id, roadmap_id=active_roadmap.id, entry_date=today)
        .first()
    )
    already_checked_in = existing_entry is not None

    delta_days = (today - active_roadmap.start_date).days
    current_week_number = 1 if delta_days < 0 else min((delta_days // 7) + 1, 13)
    milestones = active_roadmap.milestones or []
    current_week_tasks = []
    week_index = max(current_week_number - 1, 0)
    if 0 <= week_index < len(milestones):
        current_week_tasks = milestones[week_index].get('tasks', [])

    completed_task_ids = _collect_completed_task_ids(active_roadmap.id, current_user.id)
    form = CheckInForm(obj=existing_entry)
    reflection_prompt = WEEKLY_REFLECTION_PROMPTS[current_week_number - 1] if 0 < current_week_number <= len(WEEKLY_REFLECTION_PROMPTS) else WEEKLY_REFLECTION_PROMPTS[-1]

    return render_template(
        'progress/check_in.html',
        form=form,
        active_roadmap=active_roadmap,
        current_week_tasks=current_week_tasks,
        current_week_number=current_week_number,
        reflection_prompt=reflection_prompt,
        already_checked_in=already_checked_in,
        existing_entry=existing_entry,
        completed_task_ids=completed_task_ids
    )


@progress_bp.route('/check-in', methods=['POST'], endpoint='checkin_save')
@login_required
def checkin_save():
    form = CheckInForm()
    active_roadmap = (
        PivotRoadmap.query
        .filter_by(user_id=current_user.id, is_active=True)
        .order_by(PivotRoadmap.created_at.desc())
        .first()
    )
    if not active_roadmap:
        flash('You need an active 90-Day Roadmap before logging check-ins. Generate your roadmap first.', 'info')
        return redirect(url_for('planner.roadmap_form'))

    today = date.today()
    delta_days = (today - active_roadmap.start_date).days
    current_week_number = 1 if delta_days < 0 else min((delta_days // 7) + 1, 13)
    milestones = active_roadmap.milestones or []
    week_index = max(current_week_number - 1, 0)
    current_week_tasks = milestones[week_index].get('tasks', []) if 0 <= week_index < len(milestones) else []
    reflection_prompt = WEEKLY_REFLECTION_PROMPTS[current_week_number - 1] if 0 < current_week_number <= len(WEEKLY_REFLECTION_PROMPTS) else WEEKLY_REFLECTION_PROMPTS[-1]
    completed_task_ids = _collect_completed_task_ids(active_roadmap.id, current_user.id)

    if not form.validate_on_submit():
        flash('Please correct the errors below and submit again.', 'danger')
        return render_template(
            'progress/check_in.html',
            form=form,
            active_roadmap=active_roadmap,
            current_week_tasks=current_week_tasks,
            current_week_number=current_week_number,
            reflection_prompt=reflection_prompt,
            already_checked_in=False,
            existing_entry=None,
            completed_task_ids=completed_task_ids
        )

    submitted_tasks = {str(tid) for tid in request.form.getlist('tasks_completed')}
    existing_entry = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id, roadmap_id=active_roadmap.id, entry_date=today)
        .first()
    )

    if not existing_entry:
        existing_entry = ProgressEntry(
            user_id=current_user.id,
            roadmap_id=active_roadmap.id,
            entry_date=today
        )
        db_add = True
    else:
        db_add = False

    prior_completed = _collect_completed_task_ids(active_roadmap.id, current_user.id)
    merged_tasks = set(prior_completed)
    merged_tasks.update(submitted_tasks)

    existing_entry.tasks_completed = list(merged_tasks)
    existing_entry.reflection = form.reflection.data
    existing_entry.mood_rating = form.mood_rating.data
    existing_entry.obstacles_noted = form.obstacles_noted.data

    total_tasks = sum(len(week.get('tasks', [])) for week in milestones)
    overall_progress_pct = round((len(merged_tasks) / total_tasks) * 100, 2) if total_tasks else 0
    active_roadmap.overall_progress_pct = overall_progress_pct

    if db_add:
        db.session.add(existing_entry)
    db.session.commit()

    mood_rating = form.mood_rating.data
    if mood_rating <= 2:
        flash('Check-in logged. Tough weeks are part of every pivot. The important thing is you showed up.', 'info')
    elif mood_rating == 3:
        flash('Check-in saved. Steady progress is still progress. Keep going.', 'success')
    else:
        flash('Great check-in! Strong momentum this week.', 'success')

    if form.reflection.data:
        insight = ai_service.generate_reflection_insight(form.reflection.data, current_week_number, mood_rating)
        flash(insight, 'info')

    return redirect(url_for('progress.progress_dashboard'))


@progress_bp.route('/history', methods=['GET'], endpoint='progress_history')
@login_required
def progress_history():
    if request.args.get('export'):
        if not current_user.is_premium:
            flash('Exporting your progress history is a premium feature. Upgrade to download your full journal.', 'warning')
            return redirect(url_for('main.pricing'))
        return redirect(url_for('progress.export_progress'))

    page = max(int(request.args.get('page', 1)), 1)
    pagination = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id)
        .order_by(ProgressEntry.entry_date.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )
    entries = pagination.items

    total_entries_count = ProgressEntry.query.filter_by(user_id=current_user.id).count()
    max_streak = _longest_weekly_streak(entries if pagination.pages == 1 else ProgressEntry.query.filter_by(user_id=current_user.id).order_by(ProgressEntry.entry_date.desc()).all())
    moods = [e.mood_rating for e in ProgressEntry.query.filter_by(user_id=current_user.id).filter(ProgressEntry.mood_rating.isnot(None)).all()]
    avg_mood = sum(moods) / len(moods) if moods else 0

    for entry in entries:
        roadmap = entry.roadmap
        entry.week_number = _compute_week_number(roadmap, entry.entry_date)
        entry.completed_task_count = len(entry.tasks_completed or [])
        task_lookup = _task_lookup_from_milestones(roadmap.milestones if roadmap else [])
        entry.completed_task_details = [(tid, task_lookup.get(str(tid), f"Task {tid}")) for tid in (entry.tasks_completed or [])]

    return render_template(
        'progress/history.html',
        entries=entries,
        pagination=pagination,
        total_entries_count=total_entries_count,
        max_streak=max_streak,
        avg_mood=avg_mood
    )


@progress_bp.route('/journal', methods=['GET'], endpoint='journal_view')
@login_required
def journal_view():
    if request.args.get('export'):
        if not current_user.is_premium:
            flash('Exporting your journal is a premium feature. Upgrade to unlock downloads.', 'warning')
            return redirect(url_for('main.pricing'))
        return redirect(url_for('progress.export_progress'))

    page = max(int(request.args.get('page', 1)), 1)
    base_query = ProgressEntry.query.filter(
        ProgressEntry.user_id == current_user.id,
        ProgressEntry.reflection.isnot(None),
        ProgressEntry.reflection != ''
    ).order_by(ProgressEntry.entry_date.desc())
    pagination = base_query.paginate(page=page, per_page=15, error_out=False)
    entries = pagination.items

    total_with_reflections = base_query.count()
    recent_moods = base_query.limit(4).all()
    mood_distribution = {i: 0 for i in range(1, 6)}
    for entry in base_query.all():
        if entry.mood_rating:
            mood_distribution[entry.mood_rating] = mood_distribution.get(entry.mood_rating, 0) + 1
    most_common_mood = max(mood_distribution, key=lambda k: mood_distribution[k]) if mood_distribution else None
    mood_label_map = {
        1: 'Struggling',
        2: 'Difficult',
        3: 'Okay',
        4: 'Good',
        5: 'Great'
    }

    return render_template(
        'progress/journal.html',
        entries=entries,
        pagination=pagination,
        total_with_reflections=total_with_reflections,
        mood_distribution=mood_distribution,
        most_common_mood_label=mood_label_map.get(most_common_mood),
        recent_moods=recent_moods
    )


@progress_bp.route('/export', methods=['GET'], endpoint='export_progress')
@login_required
def export_progress():
    if not current_user.is_premium:
        flash('Exporting progress is a premium feature. Upgrade to unlock unlimited exports.', 'warning')
        return redirect(url_for('main.pricing'))

    entries = ProgressEntry.query.filter_by(user_id=current_user.id).order_by(ProgressEntry.entry_date.asc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'week_number', 'mood_rating', 'tasks_completed_count', 'reflection', 'obstacles_noted'])
    for entry in entries:
        roadmap = entry.roadmap
        week_number = _compute_week_number(roadmap, entry.entry_date)
        writer.writerow([
            entry.entry_date.isoformat(),
            week_number,
            entry.mood_rating or '',
            len(entry.tasks_completed or []),
            (entry.reflection or '').replace('\n', ' ').strip(),
            (entry.obstacles_noted or '').replace('\n', ' ').strip()
        ])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=PathMap_Progress_Export.csv'
        }
    )
