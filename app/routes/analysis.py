from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_required, current_user
from ..extensions import db
from ..forms.analysis_forms import NewAnalysisForm
from ..models.analysis import SkillTransferAnalysis
from ..models.assessment import UserAssessment
from ..models.role import Role
from ..services import skill_engine, feasibility, ai_service


analysis_bp = Blueprint('analysis', __name__)


def _first_day_of_month(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _first_day_next_month(dt: datetime) -> datetime:
    first_this_month = _first_day_of_month(dt)
    month = first_this_month.month + 1 if first_this_month.month < 12 else 1
    year = first_this_month.year if first_this_month.month < 12 else first_this_month.year + 1
    return first_this_month.replace(year=year, month=month)


def _get_or_create_assessment(user_id: int) -> UserAssessment:
    assessment = (
        UserAssessment.query
        .filter_by(user_id=user_id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    if assessment:
        return assessment
    assessment = UserAssessment(user_id=user_id, is_current=True)
    db.session.add(assessment)
    db.session.flush()
    return assessment


def _free_tier_limit_exceeded(user_id: int) -> bool:
    if current_user.is_premium:
        return False
    start_month = _first_day_of_month(datetime.utcnow())
    return SkillTransferAnalysis.query.filter(
        SkillTransferAnalysis.user_id == user_id,
        SkillTransferAnalysis.is_saved.is_(True),
        SkillTransferAnalysis.created_at >= start_month
    ).count() >= 1


@analysis_bp.route('/', endpoint='analysis_hub')
@login_required
def analysis_hub():
    analyses = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .all()
    )
    start_month = _first_day_of_month(datetime.utcnow())
    monthly_used = (
        SkillTransferAnalysis.query
        .filter(
            SkillTransferAnalysis.user_id == current_user.id,
            SkillTransferAnalysis.is_saved.is_(True),
            SkillTransferAnalysis.created_at >= start_month
        )
        .count()
    )
    can_create_new = current_user.is_premium or monthly_used < 1
    next_reset = _first_day_next_month(datetime.utcnow()).date()
    monthly_limit = None if current_user.is_premium else 1
    return render_template(
        'analysis/hub.html',
        analyses=analyses,
        can_create_new=can_create_new,
        is_premium=current_user.is_premium,
        monthly_used=monthly_used,
        monthly_limit=monthly_limit,
        next_reset=next_reset
    )


@analysis_bp.route('/new', methods=['GET'], endpoint='new_analysis')
@login_required
def new_analysis():
    roles = Role.query.filter_by(is_active=True).order_by(Role.category.asc(), Role.title.asc()).all()
    roles_by_category = {}
    for role in roles:
        roles_by_category.setdefault(role.category, []).append(role)

    assessment = _get_or_create_assessment(current_user.id)
    if not assessment.skills_completed:
        flash('Skills module is not complete. We will use baseline defaults for this analysis.', 'info')

    form = NewAnalysisForm()
    return render_template(
        'analysis/new.html',
        form=form,
        roles_by_category=roles_by_category,
        user_current_role_id=current_user.current_role_id,
        is_premium=current_user.is_premium
    )


@analysis_bp.route('/new', methods=['POST'], endpoint='create_analysis')
@login_required
def create_analysis():
    form = NewAnalysisForm()
    if not form.validate_on_submit():
        flash('Please select your current role and at least one target role.', 'danger')
        return redirect(url_for('analysis.new_analysis'))

    if _free_tier_limit_exceeded(current_user.id):
        flash("You've used your 1 free analysis this month. Upgrade to Premium for unlimited analyses (₹1,499/month).", 'warning')
        return redirect(url_for('main.pricing'))

    origin_role_id = form.cleaned_origin_id
    target_role_ids = form.cleaned_target_ids

    assessment = _get_or_create_assessment(current_user.id)
    user_skills = (assessment.skills_data or {}).get('ratings', {}) if assessment.skills_completed else {}

    created_analyses = []
    for target_role_id in target_role_ids:
        transfer_result = skill_engine.compute_skill_transfer(origin_role_id, target_role_id, user_skills)
        analysis = SkillTransferAnalysis(
            user_id=current_user.id,
            origin_role_id=origin_role_id,
            target_role_id=target_role_id,
            created_at=datetime.utcnow(),
            transfer_score=transfer_result['transfer_score'],
            gap_score=transfer_result['gap_score'],
            direct_skills=transfer_result['direct_skills'],
            partial_skills=transfer_result['partial_skills'],
            gap_skills=transfer_result['gap_skills'],
            estimated_learning_hours=transfer_result['estimated_learning_hours'],
            is_saved=True
        )
        db.session.add(analysis)
        db.session.flush()
        try:
            feasibility_result = feasibility.compute_feasibility_score(analysis.id, assessment.id)
        except Exception:
            feasibility_result = None
        if feasibility_result:
            analysis.feasibility_score = feasibility_result['composite_score']
            analysis.feasibility_breakdown = feasibility_result['breakdown']
            analysis.feasibility_narrative = feasibility_result['narrative']
        created_analyses.append(analysis)

    db.session.commit()
    if created_analyses:
        flash(f"Created {len(created_analyses)} analysis{'es' if len(created_analyses) > 1 else ''}.", 'success')
        return redirect(url_for('analysis.analysis_detail', analysis_id=created_analyses[0].id))

    flash('Unable to create analysis. Please try again.', 'danger')
    return redirect(url_for('analysis.new_analysis'))


@analysis_bp.route('/<int:analysis_id>', methods=['GET'], endpoint='analysis_detail')
@login_required
def analysis_detail(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)

    assessment = _get_or_create_assessment(current_user.id)
    base_skills = (assessment.skills_data or {}).get('ratings', {}) if assessment.skills_completed else {}
    merged_skills = {**base_skills, **(analysis.user_skill_overrides or {})}
    top_skills_for_slider = skill_engine.get_top_skills_for_slider(merged_skills, analysis.target_role_id, limit=10)

    other_analyses = (
        SkillTransferAnalysis.query
        .filter(
            SkillTransferAnalysis.user_id == current_user.id,
            SkillTransferAnalysis.is_saved.is_(True),
            SkillTransferAnalysis.id != analysis.id
        )
        .order_by(SkillTransferAnalysis.created_at.desc())
        .all()
    )

    return render_template(
        'analysis/detail.html',
        analysis=analysis,
        origin_role=analysis.origin_role,
        target_role=analysis.target_role,
        direct_skills=analysis.direct_skills or [],
        partial_skills=analysis.partial_skills or [],
        gap_skills=analysis.gap_skills or [],
        top_skills_for_slider=top_skills_for_slider,
        feasibility_score=analysis.feasibility_score,
        feasibility_breakdown=analysis.feasibility_breakdown,
        transfer_score=analysis.transfer_score,
        gap_score=analysis.gap_score,
        estimated_learning_hours=analysis.estimated_learning_hours,
        other_analyses_for_compare=other_analyses,
        is_premium=current_user.is_premium
    )


@analysis_bp.route('/<int:analysis_id>/adjust', methods=['POST'], endpoint='adjust_skills')
@login_required
def adjust_skills(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)

    data = request.get_json(silent=True) or {}
    reset_requested = bool(data.get('reset'))

    assessment = _get_or_create_assessment(current_user.id)

    if reset_requested:
        base_skills = (assessment.skills_data or {}).get('ratings', {}) if assessment.skills_completed else {}
        transfer_result = skill_engine.compute_skill_transfer(analysis.origin_role_id, analysis.target_role_id, base_skills, overrides={})
        analysis.user_skill_overrides = {}
    else:
        skill_name = (data.get('skill_name') or '').strip()
        try:
            new_rating = int(data.get('new_rating'))
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid rating value.'}), 400
        overrides = analysis.user_skill_overrides or {}
        overrides[skill_name] = new_rating
        transfer_result = skill_engine.recompute_with_overrides(analysis_id, overrides)

    try:
        feasibility_result = feasibility.compute_feasibility_score(analysis_id, assessment.id)
        analysis.transfer_score = transfer_result['transfer_score']
        analysis.gap_score = transfer_result['gap_score']
        analysis.direct_skills = transfer_result['direct_skills']
        analysis.partial_skills = transfer_result['partial_skills']
        analysis.gap_skills = transfer_result['gap_skills']
        analysis.estimated_learning_hours = transfer_result['estimated_learning_hours']
        analysis.feasibility_score = feasibility_result['composite_score']
        analysis.feasibility_breakdown = feasibility_result['breakdown']
        analysis.feasibility_narrative = feasibility_result['narrative']
        db.session.commit()
        return jsonify({
            'success': True,
            'transfer_score': transfer_result['transfer_score'],
            'gap_score': transfer_result['gap_score'],
            'direct_skills': transfer_result['direct_skills'],
            'partial_skills': transfer_result['partial_skills'],
            'gap_skills': transfer_result['gap_skills'],
            'feasibility_score': feasibility_result['composite_score'],
            'feasibility_breakdown': feasibility_result['breakdown'],
            'estimated_learning_hours': transfer_result['estimated_learning_hours']
        })
    except Exception as exc:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(exc)}), 500


@analysis_bp.route('/compare', methods=['GET'], endpoint='compare_analyses')
@login_required
def compare_analyses():
    raw_ids = (request.args.get('analysis_ids') or '').split(',')
    try:
        ids = [int(x) for x in raw_ids if x.strip()][:3]
    except Exception:
        flash('Invalid analysis selection.', 'danger')
        return redirect(url_for('analysis.analysis_hub'))

    if not ids:
        flash('Select at least two analyses to compare.', 'danger')
        return redirect(url_for('analysis.analysis_hub'))
    if len(ids) > 3:
        ids = ids[:3]

    analyses = SkillTransferAnalysis.query.filter(
        SkillTransferAnalysis.id.in_(ids),
        SkillTransferAnalysis.user_id == current_user.id,
        SkillTransferAnalysis.is_saved.is_(True)
    ).all()

    if len(analyses) < len(ids):
        flash('Some analyses could not be found.', 'danger')
        return redirect(url_for('analysis.analysis_hub'))

    origin_role = analyses[0].origin_role if analyses else None
    comparisons = []
    for item in analyses:
        comparisons.append({
            'analysis': item,
            'target_role': item.target_role,
            'transfer_score': item.transfer_score,
            'gap_score': item.gap_score,
            'feasibility_score': item.feasibility_score,
            'direct_count': len(item.direct_skills or []),
            'partial_count': len(item.partial_skills or []),
            'gap_count': len(item.gap_skills or []),
            'top_gap_skills': (item.gap_skills or [])[:5]
        })

    return render_template(
        'analysis/compare.html',
        comparisons=comparisons,
        origin_role=origin_role,
        is_premium=current_user.is_premium
    )


@analysis_bp.route('/<int:analysis_id>/market-insights', methods=['POST'], endpoint='market_insights_ajax')
@login_required
def market_insights_ajax(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)
    try:
        insights = ai_service.get_job_market_insights(analysis.target_role.title)
        return jsonify({'success': True, 'insights': insights, 'role_title': analysis.target_role.title})
    except Exception:
        return jsonify({'success': False, 'insights': 'Market insights are temporarily unavailable. Please try again.'}), 500


@analysis_bp.route('/<int:analysis_id>/delete', methods=['POST'], endpoint='delete_analysis')
@login_required
def delete_analysis(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)
    analysis.is_saved = False
    db.session.commit()
    flash('Analysis deleted.', 'success')
    return redirect(url_for('analysis.analysis_hub'))


@analysis_bp.route('/<int:analysis_id>/what-if', methods=['POST'], endpoint='whatif_feasibility')
@login_required
def whatif_feasibility(analysis_id: int):
    analysis = SkillTransferAnalysis.query.get_or_404(analysis_id)
    if analysis.user_id != current_user.id:
        abort(403)

    data = request.get_json(silent=True) or {}
    overrides = {}
    for key in ['timeline_months', 'hours_per_week', 'income_floor']:
        if key in data and data.get(key) is not None:
            try:
                overrides[key] = float(data.get(key)) if key != 'timeline_months' else int(data.get(key))
            except Exception:
                continue
    try:
        result = feasibility.recompute_feasibility_with_what_if(analysis_id, overrides)
        return jsonify({'success': True, **result})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
