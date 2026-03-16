from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models.role import Role
from ..models.assessment import UserAssessment
from ..forms.auth_forms import OnboardingForm


onboarding_bp = Blueprint('onboarding', __name__)


ROLE_CATEGORIES = [
    'Technology', 'Finance', 'Healthcare', 'Creative & Design', 'Business & Strategy',
    'Education', 'Legal', 'Marketing & Growth', 'Operations', 'Other'
]

PIVOT_MOTIVATIONS = {
    'feeling_stuck', 'automation_threat', 'better_income', 'passion_mismatch',
    'burnout', 'returning_to_work', 'early_career_regret', 'other'
}


@onboarding_bp.route('/')
@login_required
def onboarding_start():
    if current_user.onboarding_complete:
        return redirect(url_for('dashboard.main_dashboard'))
    form = OnboardingForm()
    return render_template(
        'onboarding/onboarding.html',
        title='Onboarding',
        user=current_user,
        step=1,
        role_categories=ROLE_CATEGORIES,
        form=form
    )


@onboarding_bp.route('/step/1', methods=['POST'])
@login_required
def onboarding_step1():
    form = OnboardingForm()
    current_role_category = (request.form.get('current_role_category') or '').strip()
    years_experience_raw = request.form.get('years_experience')
    pivot_motivation = (request.form.get('pivot_motivation') or '').strip()

    try:
        years_experience = int(years_experience_raw)
    except (TypeError, ValueError):
        years_experience = None

    if not current_role_category or current_role_category not in ROLE_CATEGORIES:
        flash('Please select your current role category.', 'danger')
        return redirect(url_for('onboarding.onboarding_start'))

    if years_experience is None or years_experience < 0 or years_experience > 30:
        flash('Please provide your years of experience (0-30).', 'danger')
        return redirect(url_for('onboarding.onboarding_start'))

    if not pivot_motivation or pivot_motivation not in PIVOT_MOTIVATIONS:
        flash('Please choose your main motivation for pivoting.', 'danger')
        return redirect(url_for('onboarding.onboarding_start'))

    current_user.pivot_motivation = pivot_motivation
    current_user.years_experience = years_experience
    db.session.commit()

    session['onboarding_step1_category'] = current_role_category
    return redirect(url_for('onboarding.onboarding_step2'))


@onboarding_bp.route('/step/2')
@login_required
def onboarding_step2():
    if current_user.years_experience is None:
        return redirect(url_for('onboarding.onboarding_start'))
    form = OnboardingForm()
    roles = Role.query.filter_by(is_active=True).order_by(Role.category, Role.title).all()
    roles_by_category = {}
    for role in roles:
        roles_by_category.setdefault(role.category, []).append(role)
    current_category = session.get('onboarding_step1_category', '')
    return render_template(
        'onboarding/onboarding.html',
        title='Onboarding',
        user=current_user,
        step=2,
        roles_by_category=roles_by_category,
        current_category=current_category,
        form=form
    )


@onboarding_bp.route('/step/2', methods=['POST'])
@login_required
def onboarding_step2_save():
    role_id_raw = request.form.get('current_role_id')
    try:
        role_id = int(role_id_raw)
    except (TypeError, ValueError):
        flash('Please select your current role.', 'danger')
        return redirect(url_for('onboarding.onboarding_step2'))

    role = Role.query.filter_by(id=role_id, is_active=True).first()
    if not role:
        flash('Please choose a valid active role.', 'danger')
        return redirect(url_for('onboarding.onboarding_step2'))

    current_user.current_role_id = role_id
    db.session.commit()
    return redirect(url_for('onboarding.onboarding_step3'))


@onboarding_bp.route('/step/3')
@login_required
def onboarding_step3():
    if current_user.current_role_id is None:
        return redirect(url_for('onboarding.onboarding_step2'))
    form = OnboardingForm()
    selected_role = Role.query.get(current_user.current_role_id)
    return render_template(
        'onboarding/onboarding.html',
        title='Onboarding',
        user=current_user,
        step=3,
        selected_role=selected_role,
        form=form
    )


@onboarding_bp.route('/complete', methods=['POST'])
@login_required
def onboarding_complete():
    form = OnboardingForm()
    target_interests = (request.form.get('target_interests') or '').strip()
    if target_interests:
        session['target_interests'] = target_interests
    biggest_challenge = (request.form.get('biggest_challenge') or '').strip()
    if biggest_challenge:
        session['onboarding_biggest_challenge'] = biggest_challenge

    current_user.onboarding_complete = True
    existing_current = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).all()
    for assess in existing_current:
        assess.is_current = False
    assessment = UserAssessment(user_id=current_user.id, is_current=True)
    db.session.add(assessment)
    db.session.commit()

    flash(
        f"Welcome to PathMap, {current_user.first_name or 'there'}! Let's start by understanding what you really want from your career.",
        'success'
    )
    return redirect(url_for('assessment.assessment_hub'))
