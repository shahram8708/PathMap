from datetime import datetime
from typing import Dict, List, Tuple
from sqlalchemy.orm import joinedload
from ..extensions import db
from ..models.analysis import SkillTransferAnalysis
from ..models.assessment import UserAssessment
from ..models.role import RoleSkillRequirement, Skill, LearningResource
from .assessment_proc import SKILL_CATEGORIES, _snake_key


SKILL_ADJACENCY: Dict[str, List[str]] = {
    'Written Communication': ['Content Creation', 'Storytelling', 'Research & Synthesis', 'Visual Communication'],
    'Verbal Presentation': ['Storytelling', 'Stakeholder Management', 'Active Listening', 'Negotiation'],
    'Stakeholder Management': ['Negotiation', 'Team Management', 'Verbal Presentation', 'Strategic Planning', 'Active Listening'],
    'Negotiation': ['Stakeholder Management', 'Decision Making Under Pressure', 'Strategic Planning', 'Active Listening'],
    'Active Listening': ['Customer Research', 'Stakeholder Management', 'Verbal Presentation', 'Mentoring & Coaching'],
    'Data Analysis': ['Excel & Spreadsheets', 'SQL & Databases', 'Data Visualization', 'Financial Modeling', 'Research & Synthesis'],
    'Critical Thinking': ['Problem Solving', 'Research & Synthesis', 'Decision Making Under Pressure', 'Strategic Planning'],
    'Problem Solving': ['Critical Thinking', 'Design Thinking', 'Product Development', 'Operations & Process'],
    'Financial Modeling': ['Excel & Spreadsheets', 'Data Analysis', 'Finance & Accounting', 'SQL & Databases', 'Research & Synthesis'],
    'Research & Synthesis': ['Customer Research', 'Written Communication', 'Data Analysis', 'Design Thinking'],
    'Python Programming': ['Data Analysis', 'SQL & Databases', 'Digital Tools & SaaS', 'Data Visualization', 'Problem Solving'],
    'SQL & Databases': ['Data Analysis', 'Python Programming', 'Excel & Spreadsheets', 'Operations & Process'],
    'Excel & Spreadsheets': ['Data Analysis', 'Financial Modeling', 'SQL & Databases', 'Operations & Process'],
    'Data Visualization': ['Data Analysis', 'Storytelling', 'Python Programming', 'Content Creation'],
    'Digital Tools & SaaS': ['Project Management', 'Operations & Process', 'Data Analysis', 'Content Creation'],
    'Design Thinking': ['Customer Research', 'Product Development', 'Ideation & Brainstorming', 'Storytelling', 'Marketing & Growth'],
    'Content Creation': ['Storytelling', 'Written Communication', 'Visual Communication', 'Marketing & Growth'],
    'Visual Communication': ['Content Creation', 'Storytelling', 'Data Visualization', 'Design Thinking'],
    'Storytelling': ['Content Creation', 'Written Communication', 'Verbal Presentation', 'Marketing & Growth'],
    'Ideation & Brainstorming': ['Design Thinking', 'Product Development', 'Content Creation', 'Strategic Planning'],
    'Team Management': ['Mentoring & Coaching', 'Stakeholder Management', 'Project Management', 'Decision Making Under Pressure'],
    'Project Management': ['Operations & Process', 'Strategic Planning', 'Team Management', 'Product Development', 'Decision Making Under Pressure'],
    'Strategic Planning': ['Project Management', 'Decision Making Under Pressure', 'Team Management', 'Finance & Accounting'],
    'Mentoring & Coaching': ['Team Management', 'Stakeholder Management', 'Active Listening', 'Decision Making Under Pressure'],
    'Decision Making Under Pressure': ['Strategic Planning', 'Operations & Process', 'Stakeholder Management', 'Team Management'],
    'Marketing & Growth': ['Content Creation', 'Data Analysis', 'Customer Research', 'Storytelling', 'Digital Tools & SaaS'],
    'Finance & Accounting': ['Financial Modeling', 'Operations & Process', 'Data Analysis', 'Strategic Planning'],
    'Product Development': ['Design Thinking', 'Project Management', 'Data Analysis', 'Customer Research', 'Operations & Process'],
    'Operations & Process': ['Project Management', 'Strategic Planning', 'Finance & Accounting', 'Decision Making Under Pressure', 'Team Management'],
    'Customer Research': ['Research & Synthesis', 'Data Analysis', 'Design Thinking', 'Marketing & Growth', 'Active Listening']
}

_SKILL_KEY_TO_NAME = { _snake_key(skill): skill for category in SKILL_CATEGORIES.values() for skill in category }


def _normalize_skills(skills: Dict[str, int]) -> Dict[str, int]:
    normalized = {}
    for raw_key, value in (skills or {}).items():
        key = _SKILL_KEY_TO_NAME.get(raw_key, raw_key)
        try:
            normalized[key] = int(value)
        except Exception:
            normalized[key] = 0
    return normalized


def _importance_label(weight: float) -> str:
    if weight >= 0.7:
        return 'High'
    if weight >= 0.4:
        return 'Medium'
    return 'Low'


def _confidence_label(score: int) -> str:
    labels = {
        0: 'None',
        1: 'Beginner',
        2: 'Competent',
        3: 'Proficient',
        4: 'Expert'
    }
    return labels.get(int(score), 'None')


def _find_adjacent_skill_match(skill_name: str, user_skills: Dict[str, int]) -> Tuple[int, str]:
    adjacents = SKILL_ADJACENCY.get(skill_name, [])
    best_rating = 0
    best_adjacent = None
    for adj in adjacents:
        rating = int(user_skills.get(adj, 0))
        if rating >= 2 and rating > best_rating:
            best_rating = rating
            best_adjacent = adj
    return best_rating, best_adjacent


def compute_skill_transfer(origin_role_id: int, target_role_id: int, user_skills_data: Dict[str, int], overrides: Dict[str, int] = None) -> Dict:
    normalized_user_skills = _normalize_skills(user_skills_data)
    override_skills = _normalize_skills(overrides or {})
    merged_user_skills = {**normalized_user_skills, **override_skills}

    requirements = (
        RoleSkillRequirement.query
        .options(joinedload(RoleSkillRequirement.skill))
        .filter_by(role_id=target_role_id)
        .all()
    )

    total_weight = 0.0
    weighted_transfer_sum = 0.0
    direct_skills = []
    partial_skills = []
    gap_skills = []

    for req in requirements:
        skill_obj: Skill = req.skill
        skill_name = skill_obj.name
        importance_weight = float(req.importance_weight or 0.0)
        total_weight += importance_weight

        user_confidence = int(merged_user_skills.get(skill_name, 0))
        transfer_source = 'direct'
        adjacent_used = None
        zone = 'gap'
        coefficient = 0.0

        if skill_name in merged_user_skills:
            if user_confidence >= 3:
                coefficient = 1.0
                zone = 'direct'
            elif user_confidence >= 1:
                coefficient = 0.6
                zone = 'partial'
            else:
                coefficient = 0.0
                zone = 'gap'
        else:
            adj_rating, adj_skill = _find_adjacent_skill_match(skill_name, merged_user_skills)
            if adj_rating >= 2:
                coefficient = 0.5
                zone = 'partial'
                transfer_source = 'adjacent'
                adjacent_used = adj_skill
                user_confidence = adj_rating
            else:
                user_confidence = 0
                zone = 'gap'

        weighted_transfer_sum += coefficient * importance_weight

        base_payload = {
            'skill_name': skill_name,
            'importance_weight': importance_weight,
            'importance_label': _importance_label(importance_weight),
            'user_confidence': user_confidence,
            'confidence_label': _confidence_label(user_confidence)
        }

        if zone == 'direct':
            direct_skills.append(base_payload)
        elif zone == 'partial':
            partial_payload = {
                **base_payload,
                'transfer_source': transfer_source,
                'adjacent_skill_used': adjacent_used
            }
            partial_skills.append(partial_payload)
        else:
            resources = (
                LearningResource.query
                .filter_by(skill_id=skill_obj.id, is_active=True)
                .order_by(LearningResource.quality_rating.desc(), LearningResource.created_at.desc())
                .limit(3)
                .all()
            )
            gap_payload = {
                **base_payload,
                'learning_resources': [
                    {
                        'title': res.title,
                        'provider': res.provider,
                        'format': res.format,
                        'cost_tier': res.cost_tier,
                        'estimated_hours': res.estimated_hours,
                        'url': res.url,
                        'quality_rating': res.quality_rating
                    }
                    for res in resources
                ]
            }
            gap_skills.append(gap_payload)

    transfer_score = 0.0
    if total_weight > 0:
        transfer_score = round((weighted_transfer_sum / total_weight) * 100, 1)
    gap_score = round(100.0 - transfer_score, 1)

    gap_skills = sorted(gap_skills, key=lambda item: item['importance_weight'], reverse=True)

    estimated_learning_hours = 0.0
    for gap in gap_skills:
        resources = gap.get('learning_resources', [])
        if resources:
            estimated_learning_hours += float(resources[0].get('estimated_hours', 0) or 0)
        else:
            weight = gap.get('importance_weight', 0)
            if weight >= 0.7:
                estimated_learning_hours += 40.0
            elif weight >= 0.4:
                estimated_learning_hours += 20.0
            else:
                estimated_learning_hours += 10.0

    return {
        'transfer_score': transfer_score,
        'gap_score': gap_score,
        'direct_skills': direct_skills,
        'partial_skills': partial_skills,
        'gap_skills': gap_skills,
        'direct_count': len(direct_skills),
        'partial_count': len(partial_skills),
        'gap_count': len(gap_skills),
        'total_skills_required': len(requirements),
        'estimated_learning_hours': estimated_learning_hours
    }


def recompute_with_overrides(analysis_id: int, new_overrides_dict: Dict[str, int]) -> Dict:
    analysis = SkillTransferAnalysis.query.get(analysis_id)
    if not analysis:
        raise ValueError('Analysis not found')

    assessment = (
        UserAssessment.query
        .filter_by(user_id=analysis.user_id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    base_skills = (assessment.skills_data or {}).get('ratings', {}) if assessment else {}
    existing_overrides = analysis.user_skill_overrides or {}
    merged_overrides = {**existing_overrides, **(new_overrides_dict or {})}

    result = compute_skill_transfer(
        analysis.origin_role_id,
        analysis.target_role_id,
        base_skills,
        overrides=merged_overrides
    )

    analysis.transfer_score = result['transfer_score']
    analysis.gap_score = result['gap_score']
    analysis.direct_skills = result['direct_skills']
    analysis.partial_skills = result['partial_skills']
    analysis.gap_skills = result['gap_skills']
    analysis.estimated_learning_hours = result['estimated_learning_hours']
    analysis.user_skill_overrides = _normalize_skills(merged_overrides)
    db.session.commit()
    return result


def get_top_skills_for_slider(user_skills_data: Dict[str, int], target_role_id: int, limit: int = 10) -> List[Dict]:
    normalized_user_skills = _normalize_skills(user_skills_data)
    requirements = (
        RoleSkillRequirement.query
        .options(joinedload(RoleSkillRequirement.skill))
        .filter_by(role_id=target_role_id)
        .order_by(RoleSkillRequirement.importance_weight.desc())
        .all()
    )

    sliders = []
    for req in requirements:
        skill_name = req.skill.name
        rating = int(normalized_user_skills.get(skill_name, 0))
        zone = 'gap'
        if rating >= 3:
            zone = 'direct'
        elif rating >= 1:
            zone = 'partial'
        else:
            adj_rating, _ = _find_adjacent_skill_match(skill_name, normalized_user_skills)
            if adj_rating >= 2:
                zone = 'partial'
        sliders.append({
            'skill_name': skill_name,
            'skill_id': req.skill.id,
            'current_rating': rating,
            'importance_weight': float(req.importance_weight or 0.0),
            'importance_label': _importance_label(float(req.importance_weight or 0.0)),
            'current_zone': zone
        })

    return sliders[:limit]
