from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.analysis import SkillTransferAnalysis
from ..models.assessment import UserAssessment
from ..models.role import LearningResource, Role, Skill
from ..models.session import ResourceBookmark
from ..services.assessment_proc import SKILL_CATEGORIES


resources_bp = Blueprint('resources', __name__)


@resources_bp.route('/', methods=['GET'], endpoint='library')
@login_required
def library():
    category = request.args.get('category')
    format_type = request.args.get('format_type')
    cost_tier = request.args.get('cost_tier')
    search = request.args.get('search')
    min_rating = request.args.get('min_rating', type=float)
    page = request.args.get('page', 1, type=int)

    latest_analysis = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .first()
    )
    gap_skills = latest_analysis.gap_skills or [] if latest_analysis else []
    gap_skill_names = [item.get('skill_name') for item in gap_skills if item.get('skill_name')]
    gap_importance_map = {item.get('skill_name'): item.get('importance_weight', 0) for item in gap_skills if item.get('skill_name')}

    recommended_resources = []
    if gap_skill_names:
        recommended_resources = (
            LearningResource.query
            .join(Skill)
            .filter(LearningResource.is_active.is_(True), Skill.name.in_(gap_skill_names))
            .order_by(LearningResource.quality_rating.desc())
            .limit(40)
            .all()
        )
        recommended_resources = sorted(
            recommended_resources,
            key=lambda res: gap_importance_map.get(res.skill.name, 0),
            reverse=True
        )[:8]

    resource_query = LearningResource.query.join(Skill).options(joinedload(LearningResource.skill))
    resource_query = resource_query.filter(LearningResource.is_active.is_(True), Skill.is_active.is_(True))

    if category:
        resource_query = resource_query.filter(Skill.category == category)
    if format_type:
        resource_query = resource_query.filter(LearningResource.format == format_type)
    if cost_tier:
        if cost_tier == 'low_cost':
            resource_query = resource_query.filter(LearningResource.cost_tier.in_(['Free', 'Low Cost', 'low_cost', 'free']))
        else:
            resource_query = resource_query.filter(LearningResource.cost_tier == cost_tier)
    if search:
        like_term = f"%{search}%"
        resource_query = resource_query.filter(
            or_(Skill.name.ilike(like_term), LearningResource.title.ilike(like_term))
        )
    if min_rating:
        resource_query = resource_query.filter(LearningResource.quality_rating >= min_rating)

    resource_query = resource_query.order_by(LearningResource.quality_rating.desc())

    pagination = resource_query.paginate(page=page, per_page=15, error_out=False)
    resources = pagination.items

    is_limited = False
    if not current_user.is_premium:
        trimmed = []
        seen_counts = {}
        for res in resources:
            skill_name = res.skill.name if res.skill else 'Unknown'
            seen_counts.setdefault(skill_name, 0)
            if seen_counts[skill_name] < 2:
                trimmed.append(res)
            else:
                is_limited = True
            seen_counts[skill_name] += 1
        resources = trimmed

    skill_categories = SKILL_CATEGORIES
    format_types = ['video', 'text', 'project', 'course', 'bootcamp']
    cost_tiers = ['free', 'low_cost', 'premium']

    total_resources = LearningResource.query.filter_by(is_active=True).count()
    format_counts = dict(
        db.session.query(LearningResource.format, func.count(LearningResource.id)).group_by(LearningResource.format).all()
    )
    cost_counts = dict(
        db.session.query(LearningResource.cost_tier, func.count(LearningResource.id)).group_by(LearningResource.cost_tier).all()
    )
    library_stats = {
        'total_resources': total_resources,
        'format_counts': format_counts,
        'cost_counts': cost_counts
    }

    current_filters = {
        'category': category,
        'format_type': format_type,
        'cost_tier': cost_tier,
        'search': search,
        'min_rating': min_rating
    }

    return render_template(
        'resources/library.html',
        recommended_resources=recommended_resources,
        resources=resources,
        pagination=pagination,
        skill_categories=skill_categories,
        format_types=format_types,
        cost_tiers=cost_tiers,
        library_stats=library_stats,
        current_filters=current_filters,
        is_premium=current_user.is_premium,
        is_limited=is_limited
    )


@resources_bp.route('/create', methods=['GET', 'POST'], endpoint='create_resource')
@login_required
def create_resource():
    skills = Skill.query.filter_by(is_active=True).order_by(Skill.name.asc()).all()
    format_types = ['video', 'text', 'project', 'course', 'bootcamp']
    cost_tiers = ['free', 'low_cost', 'premium']

    if request.method == 'POST':
        form_data = {
            'skill_id': request.form.get('skill_id', type=int),
            'title': (request.form.get('title') or '').strip(),
            'provider': (request.form.get('provider') or '').strip(),
            'format_type': (request.form.get('format_type') or '').strip().lower(),
            'cost_tier': (request.form.get('cost_tier') or '').strip().lower(),
            'estimated_hours': (request.form.get('estimated_hours') or '').strip(),
            'url': (request.form.get('url') or '').strip(),
            'quality_rating': (request.form.get('quality_rating') or '').strip(),
        }

        errors = []
        skill = Skill.query.filter_by(id=form_data['skill_id'], is_active=True).first()
        if not skill:
            errors.append('Choose a valid active skill.')

        if not form_data['title']:
            errors.append('Title is required.')
        if not form_data['provider']:
            errors.append('Provider is required.')
        if not form_data['url']:
            errors.append('A resource URL is required.')

        format_value = form_data['format_type'] if form_data['format_type'] in format_types else 'course'
        cost_value = form_data['cost_tier'] if form_data['cost_tier'] in cost_tiers else 'free'

        try:
            est_hours = float(form_data['estimated_hours'])
            if est_hours <= 0:
                errors.append('Estimated hours must be greater than zero.')
        except ValueError:
            errors.append('Estimated hours must be a number.')
            est_hours = None

        quality_rating = 4.0
        if form_data['quality_rating']:
            try:
                quality_rating = float(form_data['quality_rating'])
                quality_rating = max(0.0, min(5.0, quality_rating))
            except ValueError:
                errors.append('Quality rating must be a number between 0 and 5.')

        if errors:
            return render_template(
                'resources/create.html',
                skills=skills,
                format_types=format_types,
                cost_tiers=cost_tiers,
                errors=errors,
                form_data=form_data
            ), 400

        new_resource = LearningResource(
            skill_id=skill.id,
            title=form_data['title'],
            provider=form_data['provider'],
            format=format_value,
            cost_tier=cost_value,
            estimated_hours=est_hours,
            url=form_data['url'],
            quality_rating=quality_rating,
            is_active=True
        )
        db.session.add(new_resource)
        db.session.commit()

        flash('Resource added and visible to everyone.', 'success')
        return redirect(url_for('resources.skill_resources', skill_id=skill.id))

    return render_template(
        'resources/create.html',
        skills=skills,
        format_types=format_types,
        cost_tiers=cost_tiers,
        errors=[],
        form_data={}
    )


@resources_bp.route('/skill/<int:skill_id>', methods=['GET'], endpoint='skill_resources')
@login_required
def skill_resources(skill_id: int):
    skill = Skill.query.filter_by(id=skill_id, is_active=True).first()
    if not skill:
        abort(404)

    resources_query = LearningResource.query.filter_by(skill_id=skill_id, is_active=True).order_by(LearningResource.quality_rating.desc())
    all_resources = resources_query.all()
    resources = all_resources
    is_limited = False
    if not current_user.is_premium:
        resources = all_resources[:2]
        is_limited = len(all_resources) > 2

    latest_analysis = (
        SkillTransferAnalysis.query
        .filter_by(user_id=current_user.id, is_saved=True)
        .order_by(SkillTransferAnalysis.created_at.desc())
        .first()
    )
    gap_skills = latest_analysis.gap_skills or [] if latest_analysis else []
    gap_skill_map = {item.get('skill_name'): item for item in gap_skills if item.get('skill_name')}
    gap_entry = gap_skill_map.get(skill.name)
    is_gap_skill = gap_entry is not None
    gap_importance = gap_entry.get('importance_weight') if gap_entry else None

    assessment = UserAssessment.query.filter_by(user_id=current_user.id, is_current=True).order_by(UserAssessment.created_at.desc()).first()
    skills_data = assessment.skills_data if assessment and assessment.skills_data else {}
    user_skill_rating = skills_data.get(skill.name)

    related_skills = Skill.query.filter(
        Skill.category == skill.category,
        Skill.is_active.is_(True),
        Skill.id != skill.id
    ).order_by(Skill.name.asc()).all()

    return render_template(
        'resources/skill_resources.html',
        skill=skill,
        resources=resources,
        all_count=len(all_resources),
        is_premium=current_user.is_premium,
        is_gap_skill=is_gap_skill,
        gap_importance=gap_importance,
        user_skill_rating=user_skill_rating,
        is_limited=is_limited,
        related_skills=related_skills
    )


@resources_bp.route('/category/<string:category_name>', methods=['GET'], endpoint='category_resources')
@login_required
def category_resources(category_name: str):
    if category_name not in SKILL_CATEGORIES.keys():
        abort(404)

    skills = Skill.query.filter_by(category=category_name, is_active=True).order_by(Skill.name.asc()).all()
    skills_with_resources = []
    is_limited = False
    for skill in skills:
        res_query = LearningResource.query.filter_by(skill_id=skill.id, is_active=True).order_by(LearningResource.quality_rating.desc())
        res_list = res_query.all()
        if not current_user.is_premium:
            if len(res_list) > 2:
                is_limited = True
            res_list = res_list[:2]
        skills_with_resources.append((skill, res_list))

    return render_template(
        'resources/category.html',
        category_name=category_name,
        skills_with_resources=skills_with_resources,
        is_premium=current_user.is_premium,
        is_limited=is_limited
    )


@resources_bp.route('/bookmark/<int:resource_id>', methods=['POST'], endpoint='bookmark_resource')
@login_required
def bookmark_resource(resource_id: int):
    resource = LearningResource.query.get_or_404(resource_id)
    bookmark = ResourceBookmark.query.filter_by(user_id=current_user.id, resource_id=resource_id).first()

    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({'success': True, 'bookmarked': False})

    if not current_user.is_premium:
        existing_count = ResourceBookmark.query.filter_by(user_id=current_user.id).count()
        if existing_count >= 5:
            return jsonify({'success': False, 'limit_reached': True, 'message': 'Free plan allows up to 5 bookmarks.'}), 403

    new_bookmark = ResourceBookmark(user_id=current_user.id, resource_id=resource.id)
    db.session.add(new_bookmark)
    db.session.commit()
    return jsonify({'success': True, 'bookmarked': True})


@resources_bp.route('/bookmarks', methods=['GET'], endpoint='my_bookmarks')
@login_required
def my_bookmarks():
    bookmarks = (
        ResourceBookmark.query
        .options(joinedload(ResourceBookmark.resource).joinedload(LearningResource.skill))
        .filter_by(user_id=current_user.id)
        .order_by(ResourceBookmark.bookmarked_at.desc())
        .all()
    )
    return render_template('resources/bookmarks.html', bookmarks=bookmarks, is_premium=current_user.is_premium)


@resources_bp.route('/search', methods=['GET'], endpoint='search_resources')
@login_required
def search_resources():
    query = request.args.get('q', '', type=str)
    if not query or len(query) < 2:
        return jsonify([])
    like_term = f"%{query}%"
    results = (
        db.session.query(Skill.name, LearningResource.title, LearningResource.provider, LearningResource.format, LearningResource.cost_tier, Skill.id)
        .join(LearningResource, LearningResource.skill_id == Skill.id)
        .filter(
            LearningResource.is_active.is_(True),
            or_(Skill.name.ilike(like_term), LearningResource.title.ilike(like_term))
        )
        .order_by(LearningResource.quality_rating.desc())
        .limit(10)
        .all()
    )

    response = []
    for skill_name, title, provider, fmt, cost, skill_id in results:
        response.append({
            'skill_name': skill_name,
            'resource_title': title,
            'provider': provider,
            'format': fmt,
            'cost_tier': cost,
            'url': url_for('resources.skill_resources', skill_id=skill_id)
        })
    return jsonify(response)