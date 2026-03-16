import json
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from ..extensions import db
from ..forms.planner_forms import RoadmapGenerationForm, DecisionStepForm
from ..models.analysis import SkillTransferAnalysis
from ..models.assessment import UserAssessment
from ..models.roadmap import PivotRoadmap, ProgressEntry
from ..models.role import Role
from ..services import ai_service, roadmap_gen
from ..services.pdf_service import generate_decision_pdf
from ..utils.decorators import premium_required, assessment_required, analysis_required


planner_bp = Blueprint('planner', __name__)


def _load_current_assessment():
    return (
        UserAssessment.query
        .filter_by(user_id=current_user.id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )


def _parse_decision_summary(raw_summary):
    if not raw_summary:
        return {}
    if isinstance(raw_summary, dict):
        return raw_summary
    try:
        return json.loads(raw_summary)
    except Exception:
        return {}


@planner_bp.route('/', methods=['GET'], endpoint='planner_hub')
@login_required
def planner_hub():
    assessment = _load_current_assessment()
    saved_analyses = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .all()
    )
    active_roadmap = PivotRoadmap.query.filter_by(user_id=current_user.id, is_active=True).first()
    decision_complete = any(a.decision_completed for a in saved_analyses) if saved_analyses else False

    planner_tools = [
        {
            'name': 'Feasibility Scoring',
            'description': 'Multi-dimensional scoring of each career target against your specific profile and constraints.',
            'icon': 'bi-speedometer2',
            'status': 'available' if saved_analyses else 'locked',
            'lock_reason': 'Complete a Skill Transfer Analysis first',
            'url': url_for('analysis.analysis_hub'),
            'premium': False
        },
        {
            'name': 'Decision Confidence Framework',
            'description': 'A structured 5-step process to move from career analysis to committed decision. Based on validated decision science.',
            'icon': 'bi-check2-all',
            'status': 'available' if (saved_analyses and current_user.is_premium) else 'locked',
            'lock_reason': 'Premium feature' if not current_user.is_premium else 'Complete a Skill Transfer Analysis first',
            'url': url_for('planner.decision_framework'),
            'premium': True
        },
        {
            'name': '90-Day Pivot Roadmap',
            'description': 'Personalized weekly action plan covering skill-building, networking, and portfolio development.',
            'icon': 'bi-map',
            'status': 'available' if (saved_analyses and current_user.is_premium) else 'locked',
            'lock_reason': 'Premium feature' if not current_user.is_premium else 'Complete a Skill Transfer Analysis first',
            'url': url_for('planner.roadmap_form'),
            'premium': True
        }
    ]

    return render_template(
        'planner/hub.html',
        assessment=assessment,
        saved_analyses=saved_analyses,
        active_roadmap=active_roadmap,
        decision_complete=decision_complete,
        planner_tools=planner_tools,
        is_premium=current_user.is_premium
    )


@planner_bp.route('/decision', methods=['GET'], endpoint='decision_framework')
@login_required
@premium_required
@analysis_required
def decision_framework():
    analysis = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        flash('No saved analysis found. Please complete a Skill Transfer Analysis first.', 'warning')
        return redirect(url_for('analysis.analysis_hub'))

    assessment = _load_current_assessment()
    target_role = analysis.target_role
    origin_role = analysis.origin_role
    existing_decision_data = _parse_decision_summary(analysis.decision_summary)

    current_step = 1
    if existing_decision_data:
        completed_steps = [int(key.split('_')[1]) for key in existing_decision_data.keys() if key.startswith('step_') and existing_decision_data.get(key)]
        if completed_steps:
            current_step = min(max(completed_steps) + 1, 5)

    decision_context = {
        'analysis_id': analysis.id,
        'target_role': target_role,
        'origin_role': origin_role,
        'transfer_score': analysis.transfer_score,
        'feasibility_score': analysis.feasibility_score,
        'feasibility_breakdown': analysis.feasibility_breakdown or {},
        'top_values': (assessment.profile_summary or {}).get('top_5_values', []) if assessment else [],
        'dominant_style': (assessment.profile_summary or {}).get('dominant_style', '') if assessment else '',
        'constraints': assessment.constraints_data if assessment else {},
        'gap_skills': (analysis.gap_skills or [])[:5],
        'existing_decision_data': existing_decision_data
    }

    step_param = request.args.get('step', type=int)
    if step_param and 1 <= step_param <= 5:
        current_step = step_param

    return render_template(
        'planner/decision.html',
        decision_context=decision_context,
        current_step=current_step,
        total_steps=5,
        step_form=DecisionStepForm()
    )


@planner_bp.route('/decision/step/<int:step>', methods=['POST'], endpoint='decision_step_save')
@login_required
@premium_required
def decision_step_save(step: int):
    if step < 1 or step > 5:
        flash('Invalid decision step.', 'danger')
        return redirect(url_for('planner.decision_framework'))

    form = DecisionStepForm()
    if not form.validate_on_submit():
        flash('Please complete the step before continuing.', 'danger')
        return redirect(url_for('planner.decision_framework', step=step))

    analysis = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        flash('No saved analysis found. Please complete a Skill Transfer Analysis first.', 'warning')
        return redirect(url_for('analysis.analysis_hub'))

    assessment = _load_current_assessment()
    # Work on a fresh copy so JSON field changes are detected by SQLAlchemy
    decision_data = dict(_parse_decision_summary(analysis.decision_summary) or {})

    if step == 1:
        decision_options = [opt.strip() for opt in (request.form.getlist('decision_options[]') or request.form.getlist('decision_options')) if opt.strip()]
        step_data = {
            'real_decision': (request.form.get('real_decision') or '').strip(),
            'decision_options': decision_options,
            'decision_stakes': (request.form.get('decision_stakes') or '').strip()
        }
    elif step == 2:
        top_values = (assessment.profile_summary or {}).get('top_5_values', []) if assessment else []
        value_alignment = {}
        for idx, value_name in enumerate(top_values):
            selected = request.form.get(f'value_{idx}', '').strip()
            value_alignment[value_name] = selected
        step_data = {'values_check': value_alignment}
    elif step == 3:
        assumption_options = request.form.getlist('assumption_option[]') or request.form.getlist('assumption_option')
        assumption_texts = request.form.getlist('assumption_text[]') or request.form.getlist('assumption_text')
        assumption_conf = request.form.getlist('assumption_confidence[]') or request.form.getlist('assumption_confidence')
        assumptions = []
        for opt, text, conf in zip(assumption_options, assumption_texts, assumption_conf):
            if not text.strip():
                continue
            try:
                confidence = int(conf)
            except Exception:
                confidence = 3
            assumptions.append({
                'option': opt.strip(),
                'assumption': text.strip(),
                'confidence': max(1, min(confidence, 5))
            })
        step_data = {'assumptions': assumptions}
    elif step == 4:
        step_data = {
            'ten_days': (request.form.get('ten_days') or '').strip(),
            'ten_months': (request.form.get('ten_months') or '').strip(),
            'ten_years': (request.form.get('ten_years') or '').strip()
        }
    else:
        step_data = {
            'committed_direction': (request.form.get('committed_direction') or '').strip(),
            'commitment_note': (request.form.get('commitment_note') or '').strip()
        }

    decision_data[f'step_{step}'] = step_data
    decision_data['last_updated'] = datetime.utcnow().isoformat()

    if step == 5:
        try:
            decision_data['ai_commitment_statement'] = ai_service.generate_decision_commitment_statement(decision_data)
        except Exception:
            decision_data['ai_commitment_statement'] = 'I am committing to the direction defined above and will execute consistently for the next 90 days.'
        analysis.decision_completed = True
        flash('Your Decision Summary is ready. Download it as a PDF to keep as your personal accountability document.', 'success')

    analysis.decision_summary = decision_data
    db.session.commit()

    if step < 5:
        return redirect(url_for('planner.decision_framework', step=step + 1))
    return redirect(url_for('planner.decision_summary', analysis_id=analysis.id))


@planner_bp.route('/decision/summary/<int:analysis_id>', methods=['GET'], endpoint='decision_summary')
@login_required
@premium_required
def decision_summary(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)
    if not analysis.decision_completed:
        flash('Complete the Decision Framework before viewing the summary.', 'warning')
        return redirect(url_for('planner.decision_framework'))

    decision_data = _parse_decision_summary(analysis.decision_summary)
    target_role = analysis.target_role
    origin_role = analysis.origin_role
    assessment = _load_current_assessment()

    return render_template(
        'planner/decision_summary.html',
        analysis=analysis,
        decision_data=decision_data,
        target_role=target_role,
        origin_role=origin_role,
        assessment=assessment
    )


@planner_bp.route('/decision/summary/<int:analysis_id>/download', methods=['GET'], endpoint='download_decision_pdf')
@login_required
@premium_required
def download_decision_pdf(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)

    decision_data = _parse_decision_summary(analysis.decision_summary)
    target_role = analysis.target_role
    assessment = _load_current_assessment()
    try:
        buffer = generate_decision_pdf(current_user, analysis, decision_data, target_role, assessment)
        filename = f"PathMap_Decision_{target_role.title.replace(' ', '_')}.pdf"
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
    except Exception:
        flash('PDF generation failed. Please try again or contact support@pathmap.in.', 'danger')
        return redirect(url_for('planner.decision_summary', analysis_id=analysis.id))


@planner_bp.route('/feasibility/<int:analysis_id>', methods=['GET'], endpoint='feasibility_detail')
@login_required
def feasibility_detail(analysis_id: int):
    analysis = (
        SkillTransferAnalysis.query
        .options(joinedload(SkillTransferAnalysis.origin_role), joinedload(SkillTransferAnalysis.target_role))
        .get_or_404(analysis_id)
    )
    if analysis.user_id != current_user.id:
        abort(403)

    breakdown = analysis.feasibility_breakdown or {}
    assessment = _load_current_assessment()

    return render_template(
        'planner/feasibility_detail.html',
        analysis=analysis,
        breakdown=breakdown,
        assessment=assessment
    )


@planner_bp.route('/roadmap/new', methods=['GET'], endpoint='roadmap_form')
@login_required
@premium_required
@analysis_required
def roadmap_form():
    analyses = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .options(joinedload(SkillTransferAnalysis.target_role))
        .order_by(SkillTransferAnalysis.created_at.desc())
        .all()
    )
    form = RoadmapGenerationForm()
    form.analysis_id.choices = [(a.id, a.target_role.title) for a in analyses]
    active_roadmap = PivotRoadmap.query.filter_by(user_id=current_user.id, is_active=True).first()
    return render_template('planner/roadmap_form.html', analyses=analyses, form=form, active_roadmap=active_roadmap)


@planner_bp.route('/roadmap/new', methods=['POST'], endpoint='generate_roadmap')
@login_required
@premium_required
def generate_roadmap():
    analyses = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .options(joinedload(SkillTransferAnalysis.target_role))
        .order_by(SkillTransferAnalysis.created_at.desc())
        .all()
    )
    form = RoadmapGenerationForm()
    form.analysis_id.choices = [(a.id, a.target_role.title) for a in analyses]

    if not form.validate_on_submit():
        flash('Please correct the errors in the form.', 'danger')
        active_roadmap = PivotRoadmap.query.filter_by(user_id=current_user.id, is_active=True).first()
        return render_template('planner/roadmap_form.html', analyses=analyses, form=form, active_roadmap=active_roadmap)

    priority_total = (form.priority_skills.data or 0) + (form.priority_network.data or 0) + (form.priority_portfolio.data or 0)
    if priority_total != 100:
        flash('Skill, network, and portfolio priorities must add up to exactly 100%.', 'danger')
        active_roadmap = PivotRoadmap.query.filter_by(user_id=current_user.id, is_active=True).first()
        return render_template('planner/roadmap_form.html', analyses=analyses, form=form, active_roadmap=active_roadmap)

    analysis = SkillTransferAnalysis.query.filter_by(id=form.analysis_id.data, user_id=current_user.id, is_saved=True).first()
    if not analysis:
        flash('The selected analysis could not be found.', 'danger')
        return redirect(url_for('planner.roadmap_form'))

    start_date = form.start_date.data or date.today()
    if start_date < date.today():
        start_date = date.today()

    priority_balance = {
        'skills': form.priority_skills.data,
        'network': form.priority_network.data,
        'portfolio': form.priority_portfolio.data
    }

    PivotRoadmap.query.filter_by(user_id=current_user.id, is_active=True).update({'is_active': False})
    db.session.flush()

    milestones = roadmap_gen.generate_roadmap(
        analysis.target_role_id,
        analysis.gap_skills or [],
        form.hours_per_week.data,
        priority_balance,
        start_date
    )

    try:
        milestones = roadmap_gen.enrich_roadmap_tasks_with_ai(milestones, analysis.target_role.title, analysis.gap_skills or [])
    except Exception:
        pass

    new_roadmap = PivotRoadmap(
        user_id=current_user.id,
        target_role_id=analysis.target_role_id,
        analysis_id=analysis.id,
        start_date=start_date,
        hours_per_week=form.hours_per_week.data,
        priority_balance=priority_balance,
        milestones=milestones,
        is_active=True
    )
    db.session.add(new_roadmap)
    db.session.commit()

    flash('Your 90-Day Pivot Roadmap is ready! Week 1 starts today.', 'success')
    return redirect(url_for('planner.roadmap_detail', roadmap_id=new_roadmap.id))


@planner_bp.route('/roadmap/<int:roadmap_id>', methods=['GET'], endpoint='roadmap_detail')
@login_required
@premium_required
def roadmap_detail(roadmap_id: int):
    roadmap = PivotRoadmap.query.get_or_404(roadmap_id)
    if roadmap.user_id != current_user.id:
        abort(403)

    target_role = roadmap.target_role
    progress_entries = (
        ProgressEntry.query
        .filter_by(user_id=current_user.id, roadmap_id=roadmap.id)
        .order_by(ProgressEntry.entry_date.asc())
        .all()
    )

    days_into_pivot = max((date.today() - roadmap.start_date).days, 0)
    current_week = min((days_into_pivot // 7) + 1, 13)
    days_remaining = max(0, 90 - days_into_pivot)

    completed_task_ids = set()
    for entry in progress_entries:
        if entry.tasks_completed:
            completed_task_ids.update(entry.tasks_completed)

    milestones = roadmap.milestones or []
    total_tasks = 0
    for week in milestones:
        week_tasks = week.get('tasks', [])
        total_tasks += len(week_tasks)
        completed_in_week = 0
        for task in week_tasks:
            task_id = task.get('id')
            if task_id in completed_task_ids:
                task['is_completed'] = True
                completed_in_week += 1
            else:
                task['is_completed'] = False
        week['week_completion_pct'] = round((completed_in_week / len(week_tasks)) * 100, 2) if week_tasks else 0

    overall_progress_pct = round((len(completed_task_ids) / total_tasks) * 100, 2) if total_tasks else 0

    upcoming_checkpoint = None
    for checkpoint_day in [30, 60, 90]:
        if 0 <= (checkpoint_day - days_into_pivot) <= 7:
            upcoming_checkpoint = checkpoint_day
            break

    roadmap_summary_stats = roadmap_gen.compute_roadmap_summary_stats(milestones)

    return render_template(
        'planner/roadmap_detail.html',
        roadmap=roadmap,
        target_role=target_role,
        milestones=milestones,
        current_week=current_week,
        days_into_pivot=days_into_pivot,
        days_remaining=days_remaining,
        overall_progress_pct=overall_progress_pct,
        completed_task_ids=list(completed_task_ids),
        upcoming_checkpoint=upcoming_checkpoint,
        progress_entries_count=len(progress_entries),
        roadmap_summary_stats=roadmap_summary_stats
    )


@planner_bp.route('/roadmap/<int:roadmap_id>/complete-tasks', methods=['POST'], endpoint='complete_tasks_ajax')
@login_required
@premium_required
def complete_tasks_ajax(roadmap_id: int):
    roadmap = PivotRoadmap.query.get_or_404(roadmap_id)
    if roadmap.user_id != current_user.id:
        abort(403)

    data = request.get_json(silent=True) or {}
    task_ids = data.get('task_ids') or []
    if not isinstance(task_ids, list):
        return jsonify({'success': False, 'error': 'Invalid payload.'}), 400

    today = date.today()
    entry = ProgressEntry.query.filter_by(user_id=current_user.id, roadmap_id=roadmap.id, entry_date=today).first()
    if not entry:
        entry = ProgressEntry(user_id=current_user.id, roadmap_id=roadmap.id, entry_date=today, tasks_completed=[])
        db.session.add(entry)

    current_tasks = set(entry.tasks_completed or [])
    for task_id in task_ids:
        current_tasks.add(task_id)
    entry.tasks_completed = list(current_tasks)

    completed_task_ids = set()
    all_entries = ProgressEntry.query.filter_by(user_id=current_user.id, roadmap_id=roadmap.id).all()
    for item in all_entries:
        if item.tasks_completed:
            completed_task_ids.update(item.tasks_completed)

    total_tasks = sum(len(week.get('tasks', [])) for week in (roadmap.milestones or []))
    progress_pct = round((len(completed_task_ids) / total_tasks) * 100, 2) if total_tasks else 0

    db.session.commit()

    return jsonify({
        'success': True,
        'total_completed': len(completed_task_ids),
        'progress_pct': progress_pct
    })
