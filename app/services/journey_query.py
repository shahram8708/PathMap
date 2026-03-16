from datetime import date
from statistics import median
from ..extensions import db
from ..models.journey import Journey, JourneyView
from ..models.role import Role


JOURNEY_SORT_OPTIONS = {
    'recent': Journey.published_at.desc(),
    'timeline_shortest': Journey.timeline_months.asc(),
    'timeline_longest': Journey.timeline_months.desc(),
    'income_highest': Journey.income_change_pct.desc(),
    'most_viewed': Journey.view_count.desc()
}


def _apply_filters(base_query, filters):
    query = base_query
    if not filters:
        return query
    if filters.get('from_role_id'):
        query = query.filter(Journey.origin_role_id == filters['from_role_id'])
    if filters.get('to_role_id'):
        query = query.filter(Journey.target_role_id == filters['to_role_id'])
    outcome = filters.get('outcome')
    if outcome and outcome != 'all':
        query = query.filter(Journey.outcome_status == outcome)
    if filters.get('region'):
        query = query.filter(Journey.geographic_region == filters['region'])
    if filters.get('experience_min') is not None:
        query = query.filter(Journey.experience_at_pivot >= filters['experience_min'])
    if filters.get('experience_max') is not None:
        query = query.filter(Journey.experience_at_pivot <= filters['experience_max'])
    if filters.get('timeline_max') is not None:
        query = query.filter(Journey.timeline_months <= filters['timeline_max'])
    return query


def search_journeys(filters, page=1, per_page=10):
    filters = filters or {}
    base = Journey.query.filter_by(is_published=True)
    filtered = _apply_filters(base, filters)

    sort_key = filters.get('sort_by') or 'recent'
    order_by_expr = JOURNEY_SORT_OPTIONS.get(sort_key, JOURNEY_SORT_OPTIONS['recent'])
    paginated = filtered.order_by(order_by_expr).paginate(page=page, per_page=per_page, error_out=False)

    aggregate_query = _apply_filters(base, filters)
    stats = _compute_aggregate_stats(aggregate_query)
    return paginated, stats


def _compute_aggregate_stats(query):
    total_count = query.count()
    completed_count = query.filter(Journey.outcome_status == 'completed').count()
    in_progress_count = query.filter(Journey.outcome_status == 'in_progress').count()
    reversed_count = query.filter(Journey.outcome_status == 'reversed').count()

    timeline_values = [row[0] for row in query.with_entities(Journey.timeline_months).filter(Journey.timeline_months.isnot(None)).all()]
    median_timeline = int(median(timeline_values)) if timeline_values else None

    avg_income_change = query.filter(Journey.outcome_status == 'completed', Journey.income_change_pct.isnot(None)) \
        .with_entities(db.func.avg(Journey.income_change_pct)).scalar()

    income_positive_count = query.filter(Journey.income_change_pct > 0).count()
    income_negative_count = query.filter(Journey.income_change_pct < 0).count()

    region_row = query.with_entities(Journey.geographic_region, db.func.count(Journey.id)) \
        .group_by(Journey.geographic_region).order_by(db.func.count(Journey.id).desc()).first()
    most_common_region = region_row[0] if region_row else None

    avg_experience = query.with_entities(db.func.avg(Journey.experience_at_pivot)).scalar()

    aggregate_stats = {
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'reversed_count': reversed_count,
        'median_timeline': median_timeline,
        'avg_income_change': float(avg_income_change) if avg_income_change is not None else None,
        'income_positive_count': income_positive_count,
        'income_negative_count': income_negative_count,
        'most_common_region': most_common_region,
        'avg_experience': float(avg_experience) if avg_experience is not None else None
    }
    return aggregate_stats


def get_journey_aggregate_stats_global():
    base = Journey.query.filter_by(is_published=True)
    total_journeys = base.count()
    unique_origin_roles = base.with_entities(Journey.origin_role_id).distinct().count()
    unique_target_roles = base.with_entities(Journey.target_role_id).distinct().count()
    avg_timeline_months = base.with_entities(db.func.avg(Journey.timeline_months)).scalar()

    completed = base.filter(Journey.outcome_status == 'completed', Journey.income_change_pct.isnot(None))
    positive_income = completed.filter(Journey.income_change_pct > 0).count()
    completed_count = completed.count()
    pct_income_positive = (positive_income / completed_count * 100) if completed_count else 0

    pivot_row = base.with_entities(Journey.origin_role_id, Journey.target_role_id, db.func.count(Journey.id)) \
        .group_by(Journey.origin_role_id, Journey.target_role_id) \
        .order_by(db.func.count(Journey.id).desc()).first()
    most_common_pivot = None
    if pivot_row:
        origin_role = Role.query.get(pivot_row[0])
        target_role = Role.query.get(pivot_row[1])
        most_common_pivot = (
            origin_role.title if origin_role else None,
            target_role.title if target_role else None
        )

    reversed_pct = (base.filter(Journey.outcome_status == 'reversed').count() / total_journeys * 100) if total_journeys else 0

    return {
        'total_journeys': total_journeys,
        'unique_origin_roles': unique_origin_roles,
        'unique_target_roles': unique_target_roles,
        'avg_timeline_months': float(avg_timeline_months) if avg_timeline_months is not None else 0,
        'pct_income_positive': pct_income_positive,
        'most_common_pivot': most_common_pivot,
        'reversed_pct': reversed_pct
    }


def get_related_journeys(journey, limit=3):
    primary = Journey.query.filter(
        Journey.id != journey.id,
        Journey.is_published.is_(True),
        Journey.origin_role_id == journey.origin_role_id,
        Journey.target_role_id == journey.target_role_id
    ).order_by(Journey.published_at.desc()).limit(limit).all()

    if len(primary) >= limit:
        return primary

    supplemental_needed = limit - len(primary)
    supplemental = Journey.query.filter(
        Journey.id != journey.id,
        Journey.is_published.is_(True),
        Journey.target_role_id == journey.target_role_id
    ).order_by(Journey.published_at.desc()).limit(supplemental_needed).all()

    return primary + supplemental


def _percentiles(sorted_values, percent):
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * percent
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def get_journey_stats_for_transition(origin_role_id, target_role_id):
    q = Journey.query.filter_by(is_published=True, origin_role_id=origin_role_id, target_role_id=target_role_id)
    count = q.count()
    completed_count = q.filter(Journey.outcome_status == 'completed').count()
    reversed_count = q.filter(Journey.outcome_status == 'reversed').count()
    timelines = [row[0] for row in q.with_entities(Journey.timeline_months).filter(Journey.timeline_months.isnot(None)).all()]
    income_values = [row[0] for row in q.with_entities(Journey.income_change_pct).filter(Journey.income_change_pct.isnot(None)).all()]
    experience_values = [row[0] for row in q.with_entities(Journey.experience_at_pivot).filter(Journey.experience_at_pivot.isnot(None)).all()]

    timelines_sorted = sorted(timelines)
    median_timeline = int(median(timelines_sorted)) if timelines_sorted else None

    income_sorted = sorted(income_values)
    income_change_p25 = _percentiles(income_sorted, 0.25)
    income_change_p50 = _percentiles(income_sorted, 0.5)
    income_change_p75 = _percentiles(income_sorted, 0.75)

    avg_experience = sum(experience_values) / len(experience_values) if experience_values else None

    return {
        'count': count,
        'completed_count': completed_count,
        'reversed_count': reversed_count,
        'success_rate': (completed_count / count) if count else None,
        'median_timeline': median_timeline,
        'income_change_p25': income_change_p25,
        'income_change_p50': income_change_p50,
        'income_change_p75': income_change_p75,
        'avg_experience': avg_experience,
        'has_sufficient_data': count >= 5
    }


def check_journey_view_limit(user_id):
    today = date.today()
    views_used = JourneyView.query.filter_by(
        user_id=user_id,
        view_month=today.month,
        view_year=today.year
    ).count()
    limit_val = 5
    return {
        'views_used': views_used,
        'views_limit': limit_val,
        'views_remaining': max(0, limit_val - views_used),
        'limit_reached': views_used >= limit_val
    }


def record_journey_view(user_id, journey_id):
    today = date.today()
    existing = JourneyView.query.filter_by(
        user_id=user_id,
        journey_id=journey_id,
        view_month=today.month,
        view_year=today.year
    ).first()
    if existing:
        return existing

    view = JourneyView(
        user_id=user_id,
        journey_id=journey_id,
        view_month=today.month,
        view_year=today.year
    )
    journey = Journey.query.get(journey_id)
    if journey:
        journey.view_count = (journey.view_count or 0) + 1
    db.session.add(view)
    db.session.commit()
    return view
