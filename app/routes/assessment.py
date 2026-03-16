import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm

from app.extensions import db
from app.forms.assessment_forms import (
    WorkValuesForm,
    WorkStyleForm,
    SkillsForm,
    ConstraintsForm,
    VisionForm
)
from app.models.assessment import UserAssessment
from app.services import assessment_proc, ai_service


assessment_bp = Blueprint('assessment', __name__)


class EmptyForm(FlaskForm):
    pass


def _get_or_create_assessment():
    assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).first()
    if not assessment:
        assessment = UserAssessment(user_id=current_user.id, is_current=True)
        db.session.add(assessment)
        db.session.commit()
    return assessment


def _ensure_sequence_or_redirect(assessment, requirements):
    for condition, message, endpoint in requirements:
        if not condition:
            flash(message, 'info')
            return redirect(url_for(endpoint))
    return None


@assessment_bp.route('/', methods=['GET'], endpoint='assessment_hub')
@login_required
def assessment_hub():
    assessment = _get_or_create_assessment()
    retake_form = EmptyForm()
    modules = [
        {
            'name': 'values',
            'label': 'Work Values Survey',
            'description': 'Identify the 5 work values that matter most to you. This forms the foundation of your career profile.',
            'estimated_minutes': 4,
            'icon': 'bi-heart',
            'url': url_for('assessment.values_module'),
            'completed': assessment.values_completed,
            'locked': False
        },
        {
            'name': 'workstyle',
            'label': 'Work Style Inventory',
            'description': 'Discover your dominant work style across 4 key dimensions that determine where you thrive professionally.',
            'estimated_minutes': 5,
            'icon': 'bi-sliders',
            'url': url_for('assessment.workstyle_module'),
            'completed': assessment.workstyle_completed,
            'locked': not assessment.values_completed
        },
        {
            'name': 'skills',
            'label': 'Skill Confidence Assessment',
            'description': 'Rate your confidence across 30 professional skills. This powers the skill transfer analysis engine.',
            'estimated_minutes': 6,
            'icon': 'bi-bar-chart-steps',
            'url': url_for('assessment.skills_module'),
            'completed': assessment.skills_completed,
            'locked': not assessment.workstyle_completed
        },
        {
            'name': 'constraints',
            'label': 'Life-Stage Constraints',
            'description': 'Define your financial floor, time availability, and geographic flexibility. Keeps the analysis grounded in your real situation.',
            'estimated_minutes': 3,
            'icon': 'bi-sliders2-vertical',
            'url': url_for('assessment.constraints_module'),
            'completed': assessment.constraints_completed,
            'locked': not assessment.skills_completed
        },
        {
            'name': 'vision',
            'label': 'Career Vision',
            'description': 'Answer 3 open-ended prompts about your ideal future. PathMap AI will extract themes that guide your path comparison.',
            'estimated_minutes': 4,
            'icon': 'bi-binoculars',
            'url': url_for('assessment.vision_module'),
            'completed': assessment.vision_completed,
            'locked': not assessment.constraints_completed
        }
    ]
    total_minutes = 22
    completed_count = assessment.completed_modules_count
    completion_percentage = assessment.completion_percentage
    return render_template(
        'assessment/hub.html',
        assessment=assessment,
        modules=modules,
        total_minutes=total_minutes,
        completed_count=completed_count,
        completion_percentage=completion_percentage,
        retake_form=retake_form
    )


@assessment_bp.route('/values', methods=['GET'], endpoint='values_module')
@login_required
def values_module():
    assessment = _get_or_create_assessment()
    form = WorkValuesForm()
    existing_data = assessment.values_data or {}
    ratings = existing_data.get('ratings', {})
    for key, value in ratings.items():
        if hasattr(form, key):
            getattr(form, key).data = value
    values_list = assessment_proc.get_work_values_list()
    return render_template(
        'assessment/values.html',
        form=form,
        values_list=values_list,
        existing_data=existing_data,
        assessment=assessment
    )


@assessment_bp.route('/values', methods=['POST'], endpoint='values_save')
@login_required
def values_save():
    assessment = _get_or_create_assessment()
    form = WorkValuesForm()
    if not form.validate_on_submit():
        flash('Please rate all 10 work values before continuing.', 'danger')
        return redirect(url_for('assessment.values_module'))

    ratings = {
        'autonomy': form.autonomy.data,
        'creativity': form.creativity.data,
        'stability': form.stability.data,
        'income': form.income.data,
        'impact': form.impact.data,
        'collaboration': form.collaboration.data,
        'learning': form.learning.data,
        'prestige': form.prestige.data,
        'flexibility': form.flexibility.data,
        'social': form.social.data
    }
    values_profile = assessment_proc.compute_values_profile(ratings)
    assessment.values_data = {
        'ratings': ratings,
        'top_5': values_profile['top_5'],
        'scores': values_profile['scores'],
        'all_values_ranked': values_profile['all_values_ranked']
    }
    assessment.values_completed = True
    db.session.commit()
    flash('Work Values saved! Moving to Work Style Inventory.', 'success')
    return redirect(url_for('assessment.workstyle_module'))


@assessment_bp.route('/workstyle', methods=['GET'], endpoint='workstyle_module')
@login_required
def workstyle_module():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = WorkStyleForm()
    existing_data = assessment.workstyle_data or {}
    responses = existing_data.get('responses', {})
    for i in range(1, 13):
        key = f'q{i}'
        if key in responses:
            getattr(form, key).data = responses[key]
    questions = assessment_proc.get_workstyle_questions()
    return render_template(
        'assessment/workstyle.html',
        form=form,
        existing_data=existing_data,
        questions=questions,
        assessment=assessment
    )


@assessment_bp.route('/workstyle', methods=['POST'], endpoint='workstyle_save')
@login_required
def workstyle_save():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = WorkStyleForm()
    if not form.validate_on_submit():
        flash('Please answer all work style questions.', 'danger')
        return redirect(url_for('assessment.workstyle_module'))

    responses = {f'q{i}': getattr(form, f'q{i}').data for i in range(1, 13)}
    workstyle_profile = assessment_proc.compute_workstyle_profile(responses)
    assessment.workstyle_data = {
        'responses': responses,
        'dimension_scores': workstyle_profile['dimension_scores'],
        'dominant_style': workstyle_profile['dominant_style'],
        'secondary_style': workstyle_profile['secondary_style']
    }
    assessment.workstyle_completed = True
    db.session.commit()
    flash('Work Style saved! Next up: Skill Confidence.', 'success')
    return redirect(url_for('assessment.skills_module'))


@assessment_bp.route('/skills', methods=['GET'], endpoint='skills_module')
@login_required
def skills_module():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = SkillsForm()
    existing_data = assessment.skills_data or {}
    existing_ratings = existing_data.get('ratings', {})
    for key, value in existing_ratings.items():
        if hasattr(form, key):
            getattr(form, key).data = value
    skill_categories = assessment_proc.get_skill_categories()
    return render_template(
        'assessment/skills.html',
        form=form,
        skill_categories=skill_categories,
        existing_ratings=existing_ratings,
        assessment=assessment
    )


@assessment_bp.route('/skills', methods=['POST'], endpoint='skills_save')
@login_required
def skills_save():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = SkillsForm()
    if not form.validate_on_submit():
        flash('Please rate all 30 skills to continue.', 'danger')
        return redirect(url_for('assessment.skills_module'))

    ratings = {}
    for category, skills in assessment_proc.SKILL_CATEGORIES.items():
        for skill in skills:
            key = assessment_proc._snake_key(skill)
            ratings[key] = getattr(form, key).data

    skills_profile = assessment_proc.compute_skills_profile(ratings)
    assessment.skills_data = skills_profile
    assessment.skills_completed = True
    db.session.commit()
    flash('Skill ratings saved! Let\'s capture your constraints next.', 'success')
    return redirect(url_for('assessment.constraints_module'))


@assessment_bp.route('/constraints', methods=['GET'], endpoint='constraints_module')
@login_required
def constraints_module():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module'),
            (assessment.skills_completed, 'Please complete the Skill Confidence Assessment first.', 'assessment.skills_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = ConstraintsForm()
    existing_data = assessment.constraints_data or {}
    if existing_data:
        form.income_floor.data = existing_data.get('income_floor')
        form.hours_per_week.data = existing_data.get('hours_per_week')
        form.timeline_months.data = existing_data.get('timeline_months')
        form.geographic_flexibility.data = existing_data.get('geographic_flexibility')
    return render_template(
        'assessment/constraints.html',
        form=form,
        existing_data=existing_data,
        assessment=assessment
    )


@assessment_bp.route('/constraints', methods=['POST'], endpoint='constraints_save')
@login_required
def constraints_save():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module'),
            (assessment.skills_completed, 'Please complete the Skill Confidence Assessment first.', 'assessment.skills_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = ConstraintsForm()
    if not form.validate_on_submit():
        flash('Please complete all constraint fields with valid values.', 'danger')
        return redirect(url_for('assessment.constraints_module'))

    constraints_payload = {
        'income_floor': int(form.income_floor.data),
        'hours_per_week': int(form.hours_per_week.data),
        'timeline_months': int(form.timeline_months.data),
        'geographic_flexibility': form.geographic_flexibility.data
    }
    assessment.constraints_data = constraints_payload
    assessment.constraints_completed = True
    db.session.commit()
    flash('Constraints saved! Final step: Career Vision.', 'success')
    return redirect(url_for('assessment.vision_module'))


@assessment_bp.route('/vision', methods=['GET'], endpoint='vision_module')
@login_required
def vision_module():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module'),
            (assessment.skills_completed, 'Please complete the Skill Confidence Assessment first.', 'assessment.skills_module'),
            (assessment.constraints_completed, 'Please complete the Life-Stage Constraints first.', 'assessment.constraints_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = VisionForm()
    existing_data = assessment.vision_data or {}
    if existing_data:
        form.vision_day.data = existing_data.get('vision_day', '')
        form.vision_impact.data = existing_data.get('vision_impact', '')
        form.vision_regret.data = existing_data.get('vision_regret', '')
    return render_template(
        'assessment/vision.html',
        form=form,
        existing_data=existing_data,
        assessment=assessment
    )


@assessment_bp.route('/vision', methods=['POST'], endpoint='vision_save')
@login_required
def vision_save():
    assessment = _get_or_create_assessment()
    redirect_response = _ensure_sequence_or_redirect(
        assessment,
        [
            (assessment.values_completed, 'Please complete the Work Values Survey first.', 'assessment.values_module'),
            (assessment.workstyle_completed, 'Please complete the Work Style Inventory first.', 'assessment.workstyle_module'),
            (assessment.skills_completed, 'Please complete the Skill Confidence Assessment first.', 'assessment.skills_module'),
            (assessment.constraints_completed, 'Please complete the Life-Stage Constraints first.', 'assessment.constraints_module')
        ]
    )
    if redirect_response:
        return redirect_response

    form = VisionForm()
    if not form.validate_on_submit():
        flash('Please complete all three prompts with at least 30 characters each.', 'danger')
        return redirect(url_for('assessment.vision_module'))

    vision_payload = {
        'vision_day': form.vision_day.data.strip(),
        'vision_impact': form.vision_impact.data.strip(),
        'vision_regret': form.vision_regret.data.strip()
    }
    vision_profile = assessment_proc.compute_vision_profile(vision_payload)
    assessment.vision_data = vision_profile
    assessment.vision_completed = True

    profile_summary = assessment_proc.compute_full_profile_summary(assessment)
    try:
        ai_narrative = ai_service.generate_career_profile_narrative(profile_summary)
        profile_summary['ai_narrative'] = ai_narrative
    except Exception:
        profile_summary['ai_narrative'] = ''

    assessment.profile_summary = profile_summary
    assessment.completed_at = datetime.utcnow()
    db.session.commit()

    flash("Your Career Profile is ready! Here's what we found.", 'success')
    return redirect(url_for('assessment.assessment_results'))


@assessment_bp.route('/autosave', methods=['POST'], endpoint='autosave_module')
@login_required
def autosave_module():
    assessment = _get_or_create_assessment()
    payload = request.get_json(silent=True) or {}
    module = payload.get('module')
    data = payload.get('data', {})

    if module == 'values':
        assessment.values_data = data
    elif module == 'workstyle':
        assessment.workstyle_data = data
    elif module == 'skills':
        assessment.skills_data = data
    elif module == 'constraints':
        assessment.constraints_data = data
    elif module == 'vision':
        assessment.vision_data = data
    else:
        return jsonify({'success': False, 'error': 'Invalid module'}), 400

    db.session.commit()
    return jsonify({'success': True, 'saved_at': datetime.utcnow().isoformat()})


@assessment_bp.route('/results', methods=['GET'], endpoint='assessment_results')
@login_required
def assessment_results():
    assessment = _get_or_create_assessment()
    if not assessment.is_fully_complete or not assessment.profile_summary:
        flash('Please complete all 5 modules to see your Career Profile.', 'warning')
        return redirect(url_for('assessment.assessment_hub'))

    profile = assessment.profile_summary
    chart_data = json.dumps(profile.get('skill_category_averages', {}))
    retake_form = EmptyForm()
    return render_template(
        'assessment/results.html',
        assessment=assessment,
        profile=profile,
        top_values=profile.get('top_5_values', []),
        dominant_style=profile.get('dominant_style', ''),
        secondary_style=profile.get('secondary_style', ''),
        dimension_scores=profile.get('dimension_scores', {}),
        skill_category_averages=profile.get('skill_category_averages', {}),
        constraints=profile.get('constraints', {}),
        vision_themes=profile.get('vision_themes', []),
        ai_narrative=profile.get('ai_narrative', ''),
        chart_data=chart_data,
        next_step_url=url_for('analysis.new_analysis'),
        retake_form=retake_form
    )


@assessment_bp.route('/retake', methods=['POST'], endpoint='retake_assessment')
@login_required
def retake_assessment():
    form = EmptyForm()
    if not form.validate_on_submit():
        flash('Invalid request. Please try again.', 'danger')
        return redirect(url_for('assessment.assessment_hub'))

    assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).first()
    if assessment:
        assessment.is_current = False
        db.session.add(assessment)
        db.session.commit()

    new_assessment = UserAssessment(user_id=current_user.id, is_current=True)
    db.session.add(new_assessment)
    db.session.commit()

    flash('Assessment reset. Let\'s start fresh.', 'info')
    return redirect(url_for('assessment.assessment_hub'))
