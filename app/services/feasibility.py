from typing import Dict, List
from ..models.analysis import SkillTransferAnalysis
from ..models.assessment import UserAssessment
from ..models.journey import Journey
from ..models.role import Skill, LearningResource


def _percentile(data: List[float], percentile: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * percentile / 100
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return d0 + d1


def _time_score(timeline_months: float, hours_per_week: float, estimated_learning_hours: float) -> float:
    if estimated_learning_hours == 0:
        return 1.0
    total_available_hours = float(timeline_months or 0) * 4.33 * float(hours_per_week or 0)
    if total_available_hours <= 0:
        return 0.2
    raw_ratio = total_available_hours / estimated_learning_hours
    if raw_ratio >= 1.5:
        return 1.0
    if raw_ratio >= 1.0:
        return 0.85
    if raw_ratio >= 0.7:
        return 0.6
    if raw_ratio >= 0.5:
        return 0.4
    return 0.2


def _financial_score(income_floor: float, journeys: List[Journey]) -> float:
    baseline_income = 60000.0
    valid_changes = [j.income_change_pct for j in journeys if j.income_change_pct is not None]
    if len(valid_changes) < 3:
        return 0.5
    implied_incomes = [baseline_income * (1 + (pct / 100.0)) for pct in valid_changes]
    p25 = _percentile(implied_incomes, 25)
    p50 = _percentile(implied_incomes, 50)
    p75 = _percentile(implied_incomes, 75)
    if income_floor < p25:
        return 0.25
    if income_floor < p50:
        return 0.5
    if income_floor < p75:
        return 0.75
    return 1.0


def _historical_success_score(journeys: List[Journey]) -> float:
    published = [j for j in journeys if j.is_published]
    total = len(published)
    if total < 5:
        return 0.5
    completed = len([j for j in published if (j.outcome_status or '').lower() == 'completed'])
    return min(completed / total, 1.0)


def _resource_availability_score(gap_skills: List[Dict]) -> float:
    if not gap_skills:
        return 1.0
    top_gaps = sorted(gap_skills, key=lambda g: g.get('importance_weight', 0), reverse=True)[:5]
    scores = []
    for gap in top_gaps:
        skill_name = gap.get('skill_name')
        skill_obj = Skill.query.filter_by(name=skill_name).first()
        if not skill_obj:
            scores.append(0.0)
            continue
        resource_count = LearningResource.query.filter_by(skill_id=skill_obj.id, is_active=True).count()
        if resource_count >= 3:
            scores.append(1.0)
        elif resource_count == 2:
            scores.append(0.67)
        elif resource_count == 1:
            scores.append(0.33)
        else:
            scores.append(0.0)
    if not scores:
        return 1.0
    return sum(scores) / len(scores)


def _label_and_color(composite_score: float) -> Dict[str, str]:
    if composite_score <= 40:
        return {'label': 'Challenging', 'color': 'danger'}
    if composite_score <= 65:
        return {'label': 'Feasible with Effort', 'color': 'warning'}
    if composite_score <= 80:
        return {'label': 'Strong Match', 'color': 'success'}
    return {'label': 'Excellent Match', 'color': 'primary'}


def compute_feasibility_score(analysis_id: int, assessment_id: int) -> Dict:
    analysis = SkillTransferAnalysis.query.get(analysis_id)
    assessment = UserAssessment.query.get(assessment_id)
    if not analysis or not assessment:
        raise ValueError('Missing analysis or assessment data')

    constraints = assessment.constraints_data or {}
    timeline_months = constraints.get('timeline_months') or 0
    hours_per_week = constraints.get('hours_per_week') or 0
    income_floor = float(constraints.get('income_floor') or 0)

    journeys = (
        Journey.query
        .filter_by(origin_role_id=analysis.origin_role_id, target_role_id=analysis.target_role_id, is_published=True)
        .all()
    )

    dim_skill_gap = (analysis.transfer_score or 0.0) / 100.0
    dim_time = _time_score(timeline_months, hours_per_week, analysis.estimated_learning_hours or 0.0)
    dim_financial = _financial_score(income_floor, journeys)
    dim_success = _historical_success_score(journeys)
    dim_resources = _resource_availability_score(analysis.gap_skills or [])

    breakdown = {
        'skill_gap': {'score': dim_skill_gap, 'weight': 0.25, 'label': 'Skill Gap Score', 'icon': 'bi-diagram-3'},
        'time_feasibility': {'score': dim_time, 'weight': 0.20, 'label': 'Time Feasibility', 'icon': 'bi-clock'},
        'financial_feasibility': {'score': dim_financial, 'weight': 0.20, 'label': 'Financial Feasibility', 'icon': 'bi-currency-rupee'},
        'historical_success': {'score': dim_success, 'weight': 0.20, 'label': 'Historical Success Rate', 'icon': 'bi-people'},
        'resource_availability': {'score': dim_resources, 'weight': 0.15, 'label': 'Resource Availability', 'icon': 'bi-book'}
    }

    composite = sum(info['score'] * info['weight'] for info in breakdown.values())
    composite_score = round(composite * 100, 1)
    label_info = _label_and_color(composite_score)

    scores_for_rank = [(k, v['score']) for k, v in breakdown.items()]
    highest_dim = max(scores_for_rank, key=lambda item: item[1])
    lowest_dim = min(scores_for_rank, key=lambda item: item[1])

    suggestions = {
        'time_feasibility': 'Consider increasing your weekly hours or extending your timeline to improve this score.',
        'financial_feasibility': 'This pivot may involve a short-term income dip. Building a financial runway before starting reduces this risk.',
        'historical_success': 'Limited transition data for this path. Consider connecting with people who have made this specific pivot via the Shadow Sessions marketplace.',
        'resource_availability': 'Some of your required skill gaps have limited learning resources. Consider mentorship or project-based learning for these skills.',
        'skill_gap': 'Prioritize the highest-importance gap skills first with focused practice and feedback to raise your transfer score.'
    }

    narrative = (
        f"Your strongest area is {breakdown[highest_dim[0]]['label']} (score: {highest_dim[1]*100:.0f}%). "
        f"Your main challenge is {breakdown[lowest_dim[0]]['label']} (score: {lowest_dim[1]*100:.0f}%). "
        f"{suggestions.get(lowest_dim[0], '')}"
    )

    return {
        'composite_score': composite_score,
        'label': label_info['label'],
        'color': label_info['color'],
        'breakdown': breakdown,
        'narrative': narrative,
        'dimension_labels': {k: v['label'] for k, v in breakdown.items()}
    }


def recompute_feasibility_with_what_if(analysis_id: int, what_if_overrides: Dict) -> Dict:
    analysis = SkillTransferAnalysis.query.get(analysis_id)
    if not analysis:
        raise ValueError('Analysis not found')

    assessment = (
        UserAssessment.query
        .filter_by(user_id=analysis.user_id, is_current=True)
        .order_by(UserAssessment.created_at.desc())
        .first()
    )
    if not assessment:
        raise ValueError('Assessment not found')

    constraints = (assessment.constraints_data or {}).copy()
    overrides = what_if_overrides or {}
    if 'timeline_months' in overrides:
        constraints['timeline_months'] = overrides['timeline_months']
    if 'hours_per_week' in overrides:
        constraints['hours_per_week'] = overrides['hours_per_week']
    if 'income_floor' in overrides:
        constraints['income_floor'] = overrides['income_floor']

    journeys = (
        Journey.query
        .filter_by(origin_role_id=analysis.origin_role_id, target_role_id=analysis.target_role_id, is_published=True)
        .all()
    )

    dim_skill_gap = (analysis.transfer_score or 0.0) / 100.0
    dim_time = _time_score(constraints.get('timeline_months') or 0, constraints.get('hours_per_week') or 0, analysis.estimated_learning_hours or 0.0)
    dim_financial = _financial_score(float(constraints.get('income_floor') or 0), journeys)
    dim_success = _historical_success_score(journeys)
    dim_resources = _resource_availability_score(analysis.gap_skills or [])

    breakdown = {
        'skill_gap': {'score': dim_skill_gap, 'weight': 0.25, 'label': 'Skill Gap Score', 'icon': 'bi-diagram-3'},
        'time_feasibility': {'score': dim_time, 'weight': 0.20, 'label': 'Time Feasibility', 'icon': 'bi-clock'},
        'financial_feasibility': {'score': dim_financial, 'weight': 0.20, 'label': 'Financial Feasibility', 'icon': 'bi-currency-rupee'},
        'historical_success': {'score': dim_success, 'weight': 0.20, 'label': 'Historical Success Rate', 'icon': 'bi-people'},
        'resource_availability': {'score': dim_resources, 'weight': 0.15, 'label': 'Resource Availability', 'icon': 'bi-book'}
    }

    composite = sum(info['score'] * info['weight'] for info in breakdown.values())
    composite_score = round(composite * 100, 1)
    label_info = _label_and_color(composite_score)

    return {
        'composite_score': composite_score,
        'label': label_info['label'],
        'color': label_info['color'],
        'breakdown': breakdown,
        'dimension_labels': {k: v['label'] for k, v in breakdown.items()}
    }


def get_feasibility_improvement_suggestions(feasibility_breakdown: Dict) -> List[Dict]:
    suggestions = []
    for key, info in feasibility_breakdown.items():
        score = info.get('score', 0)
        weight = info.get('weight', 0)
        if score >= 0.65:
            continue
        potential_gain = (1 - score) * weight
        if key == 'time_feasibility':
            suggestion = 'Extend your timeline or increase weekly hours to create more capacity for learning.'
            gain_text = '+10-15 points if you extend your timeline by 6 months or add 5 hours/week.'
        elif key == 'financial_feasibility':
            suggestion = 'Re-evaluate your income floor or build a short-term financial buffer before pivoting.'
            gain_text = '+8-12 points if your income floor aligns with typical outcomes for this path.'
        elif key == 'historical_success':
            suggestion = 'Research peers who made this pivot and validate milestones through informational interviews.'
            gain_text = '+6-10 points if you add verified examples or mentors for this path.'
        elif key == 'resource_availability':
            suggestion = 'Pair limited resources with mentorship or project-based practice to close gaps faster.'
            gain_text = '+5-8 points if you secure 3 high-quality resources per gap skill.'
        else:
            suggestion = 'Focus on top gap skills first with deliberate practice and feedback loops.'
            gain_text = '+10-15 points if you move two critical gap skills to competent.'
        suggestions.append({
            'dimension': info.get('label', key),
            'current_score': score,
            'suggestion': suggestion,
            'potential_gain': gain_text,
            'impact': potential_gain
        })

    suggestions = sorted(suggestions, key=lambda item: item['impact'], reverse=True)
    return suggestions[:3]
