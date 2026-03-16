from datetime import timedelta, date
from typing import List, Dict, Any
from ..models.role import Role
from ..services import ai_service

NETWORKING_TASKS_BY_ROLE_TYPE = {
    'Technology': [
        'Join 2 developer communities (GitHub, Dev.to, relevant Discord servers)',
        'Conduct 3 informational interviews with professionals currently in {target_role}',
        'Attend 1 industry meetup or online webinar in your target field',
        'Connect with 5 {target_role} professionals on LinkedIn with a personalized note',
        'Identify and follow 3 thought leaders in {target_role} field and engage with their content'
    ],
    'Finance': [
        'Attend a finance/FinTech meetup or webinar this week and share a key insight online',
        'Conduct 2 informational interviews with professionals currently in {target_role}',
        'Join 2 finance communities (CFA local, FinTwit circles, relevant Slack groups)',
        'Connect with 5 {target_role} practitioners on LinkedIn with a specific question',
        'Follow 3 regulators or finance leaders and comment thoughtfully on their posts'
    ],
    'Healthcare': [
        'Schedule 2 conversations with clinicians or health-tech PMs working as {target_role}',
        'Join 1 healthcare product or policy community and introduce yourself',
        'Attend 1 webinar on healthcare innovation or medical regulations',
        'Connect with 5 {target_role} professionals and ask about their day-to-day realities',
        'Shadow a practitioner or request a virtual walkthrough of a healthcare workflow'
    ],
    'Creative & Design': [
        'Join 2 design communities (ADPList, Dribbble, or design Slack groups)',
        'Schedule 3 portfolio review conversations with working {target_role} designers',
        'Attend 1 design critique session or webinar this week',
        'Connect with 5 {target_role} professionals and ask about hiring expectations',
        'Engage with 3 design leaders on social by commenting with thoughtful critique'
    ],
    'Business & Strategy': [
        'Conduct 3 informational interviews with strategy or consulting professionals in {target_role}',
        'Join 1 consulting or strategy community and participate in a case discussion',
        'Attend 1 industry webinar and synthesize learnings into a short LinkedIn post',
        'Connect with 5 {target_role} leaders on LinkedIn with a concise intro and question',
        'Find and follow 3 industry analysts and summarize their recent reports'
    ],
    'Marketing & Growth': [
        'Join 2 marketing or growth communities and introduce your pivot story',
        'Conduct 3 informational interviews with growth managers focused on {target_role}',
        'Attend 1 growth-focused webinar and post a brief teardown afterward',
        'Connect with 5 {target_role} professionals on LinkedIn with a specific observation',
        'Follow 3 growth leaders and comment on their most recent case studies'
    ],
    'Education': [
        'Join 1 learning design or edtech community and request feedback on your pivot',
        'Conduct 2 informational interviews with educators working in {target_role}',
        'Attend 1 webinar on curriculum design or edtech product trends',
        'Connect with 5 {target_role} professionals to learn hiring expectations',
        'Shadow or observe an online course session to understand learner engagement'
    ],
    'Legal': [
        'Join 1 legal operations or compliance community relevant to {target_role}',
        'Conduct 2 informational interviews with legal professionals in your target area',
        'Attend 1 webinar on regulatory updates impacting {target_role}',
        'Connect with 5 {target_role} professionals on LinkedIn with a concise introduction',
        'Follow 3 legal commentators and summarize key takeaways from their posts'
    ],
    'Operations': [
        'Join an operations or supply chain community and participate in a discussion',
        'Conduct 3 informational interviews with operations leaders working as {target_role}',
        'Attend 1 webinar on process excellence or ops tooling in your industry',
        'Connect with 5 {target_role} professionals and ask about their biggest current challenge',
        'Follow 3 ops thought leaders and post your reflections on their recent content'
    ],
    'Default': [
        'Join 1 professional community aligned to your target field and introduce yourself',
        'Conduct 2 informational interviews with professionals currently in {target_role}',
        'Attend 1 industry webinar or meetup to understand the landscape',
        'Connect with 5 {target_role} professionals on LinkedIn with a personalized note',
        'Follow 3 thought leaders in the field and engage with their content twice this week'
    ]
}

PORTFOLIO_TASKS_BY_ROLE_TYPE = {
    'Technology': [
        'Build and publish 1 end-to-end portfolio project using {top_gap_skill}',
        'Write a technical blog post documenting what you built and what you learned',
        'Contribute to 1 open-source project related to {target_role} field'
    ],
    'Data & Analytics': [
        'Build 2 data analysis projects using publicly available datasets',
        'Publish your analysis with clear findings on GitHub or a portfolio blog',
        'Create a dashboard or visualization that answers a real stakeholder question'
    ],
    'Creative & Design': [
        'Complete 2 portfolio case studies in the format used by {target_role} professionals',
        'Publish your portfolio on a professional platform (Behance, Dribbble, personal site)',
        'Record a short walkthrough video explaining your design decisions'
    ],
    'Business & Strategy': [
        'Write 1 strategic analysis document on a real company or case study in your target industry',
        'Create a presentation deck demonstrating your structured thinking in target role format',
        'Design a simple operating model or roadmap for a hypothetical client'
    ],
    'Marketing & Growth': [
        'Run a small-scale campaign experiment and document the results with metrics',
        'Publish a teardown of a brand’s recent campaign relevant to {target_role}',
        'Build a mini content calendar and execute 1-2 posts with performance tracking'
    ],
    'Education': [
        'Design a mini learning module and publish it on a public platform',
        'Create 1 assessment or project that demonstrates learner outcomes for your module',
        'Record a short video walkthrough explaining your instructional choices'
    ],
    'Operations': [
        'Document and improve a real process (personal or volunteer) using ops principles',
        'Create a KPI dashboard mock-up that tracks operational health for a sample process',
        'Build a risk register and mitigation plan for a small project'
    ],
    'Default': [
        'Publish 1 tangible project that mirrors a real task in {target_role}',
        'Document the problem, your approach, and measurable outcomes in a short case study',
        'Share your project publicly and request feedback from 3 practitioners'
    ]
}

MILESTONE_CHECKPOINT_PROMPTS = {
    4: 'You are one month into your pivot. Reflect honestly: Which tasks have you completed? What has been harder than expected? Is your hours/week estimate still realistic? What one thing would make the next 30 days more effective?',
    8: 'Two months in. You should have made significant skill progress and begun networking. Reflect: Have you validated your target role choice through informational interviews or a shadow session? Are your original assumptions about this pivot still holding? What needs to change in your final 30 days?',
    13: '90 days complete. This is your full retrospective. What did you accomplish? Did you achieve what you planned? What is your next 90-day plan? Are you ready to apply to roles in {target_role}?'
}


def _slugify(text: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() or ch == ' ' else '-' for ch in text).replace(' ', '-').strip('-')


def _select_templates(category: str, mapping: Dict[str, List[str]]) -> List[str]:
    if category in mapping:
        return mapping[category]
    if category in ('Tech', 'Software'):
        return mapping.get('Technology', mapping['Default'])
    return mapping['Default']


def generate_roadmap(target_role_id: int, gap_skills: List[Dict[str, Any]], hours_per_week: int, priority_balance: Dict[str, int], start_date: date) -> List[Dict[str, Any]]:
    total_hours = hours_per_week * 13
    skills_hours = total_hours * (priority_balance.get('skills', 0) / 100)
    network_hours = total_hours * (priority_balance.get('network', 0) / 100)
    portfolio_hours = total_hours * (priority_balance.get('portfolio', 0) / 100)

    role = Role.query.get(target_role_id)
    role_title = role.title if role else 'your target role'
    role_category = role.category if role else 'Default'

    sorted_gap_skills = sorted(gap_skills or [], key=lambda x: x.get('importance_weight', 0), reverse=True)
    skill_tasks = []
    remaining_skill_hours = skills_hours
    task_counter = 1
    for skill in sorted_gap_skills:
        if remaining_skill_hours <= 0:
            break
        skill_name = skill.get('skill_name') or 'Key Skill'
        est_hours = float(skill.get('estimated_learning_hours') or 20)
        hours_to_allocate = est_hours if est_hours <= remaining_skill_hours else remaining_skill_hours
        importance_weight = skill.get('importance_weight', 0)
        importance = 'high' if importance_weight >= 0.7 else 'medium' if importance_weight >= 0.4 else 'low'
        task = {
            'id': f"skill-{task_counter}-{_slugify(skill_name)}",
            'type': 'skill',
            'title': f"Learn {skill_name}",
            'description': (
                f"Build {skill_name} competency to Proficient level (3/4). Focus on {skill.get('top_resource_title', 'the recommended resource')} by {skill.get('top_resource_provider', 'a trusted provider')}."
            ),
            'estimated_hours': round(hours_to_allocate, 1),
            'resource_link': skill.get('top_resource_url', '') or '',
            'resource_title': skill.get('top_resource_title', '') or '',
            'is_completed': False,
            'importance': importance
        }
        skill_tasks.append(task)
        remaining_skill_hours -= hours_to_allocate
        task_counter += 1

    networking_templates = _select_templates(role_category, NETWORKING_TASKS_BY_ROLE_TYPE)
    networking_tasks = []
    network_hours_remaining = network_hours
    net_idx = 1
    while network_hours_remaining > 0 and networking_templates:
        template = networking_templates[(net_idx - 1) % len(networking_templates)]
        task = {
            'id': f"network-{net_idx}",
            'type': 'network',
            'title': 'Networking Outreach',
            'description': template.format(target_role=role_title),
            'estimated_hours': 3,
            'resource_link': '',
            'resource_title': '',
            'is_completed': False,
            'importance': 'medium'
        }
        networking_tasks.append(task)
        net_idx += 1
        network_hours_remaining -= 3

    portfolio_templates = _select_templates(role_category, PORTFOLIO_TASKS_BY_ROLE_TYPE)
    top_gap_skill_name = sorted_gap_skills[0]['skill_name'] if sorted_gap_skills else 'your target skill'
    portfolio_tasks = []
    portfolio_hours_remaining = portfolio_hours
    port_idx = 1
    while portfolio_hours_remaining > 0 and portfolio_templates:
        template = portfolio_templates[(port_idx - 1) % len(portfolio_templates)]
        task = {
            'id': f"portfolio-{port_idx}",
            'type': 'portfolio',
            'title': 'Portfolio Project',
            'description': template.format(target_role=role_title, top_gap_skill=top_gap_skill_name),
            'estimated_hours': 8,
            'resource_link': '',
            'resource_title': '',
            'is_completed': False,
            'importance': 'medium'
        }
        portfolio_tasks.append(task)
        port_idx += 1
        portfolio_hours_remaining -= 8

    weeks = []
    for i in range(1, 14):
        start = start_date + timedelta(weeks=i - 1)
        end = start_date + timedelta(weeks=i)
        weeks.append({
            'week': i,
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'milestone_flag': i in (4, 8, 13),
            'checkpoint_prompt': MILESTONE_CHECKPOINT_PROMPTS.get(i, '').replace('{target_role}', role_title) if i in MILESTONE_CHECKPOINT_PROMPTS else None,
            'tasks': [],
            'total_hours': 0
        })

    def _assign_task(task, preferred_weeks):
        candidates = [weeks[i - 1] for i in preferred_weeks if 1 <= i <= 13]
        if not candidates:
            candidates = weeks
        candidates = sorted(candidates, key=lambda w: w['total_hours'])
        for candidate in candidates:
            if candidate['total_hours'] + task['estimated_hours'] <= hours_per_week + 2:
                candidate['tasks'].append(task)
                candidate['total_hours'] += task['estimated_hours']
                return
        candidates[0]['tasks'].append(task)
        candidates[0]['total_hours'] += task['estimated_hours']

    for task in skill_tasks:
        preferred_range = range(1, 7) if task.get('importance') == 'high' else range(3, 13)
        _assign_task(task, preferred_range)

    networking_blocks = [(1, 3), (4, 6), (7, 9), (10, 13)]
    remaining_network_tasks = networking_tasks.copy()
    for start_w, end_w in networking_blocks:
        if not remaining_network_tasks:
            break
        task = remaining_network_tasks.pop(0)
        _assign_task(task, range(start_w, end_w + 1))
    for task in remaining_network_tasks:
        _assign_task(task, range(1, 14))

    for task in portfolio_tasks:
        _assign_task(task, range(6, 14))

    for week in weeks:
        if week['milestone_flag']:
            checkpoint_task = {
                'id': f"checkpoint-week-{week['week']}",
                'type': 'checkpoint',
                'title': f"Day {week['week'] * 7} Milestone Review",
                'description': week['checkpoint_prompt'] or '',
                'estimated_hours': 1,
                'resource_link': '',
                'resource_title': '',
                'is_completed': False,
                'importance': 'medium'
            }
            week['tasks'] = [checkpoint_task] + week['tasks']
            week['total_hours'] += 1

    return weeks


def enrich_roadmap_tasks_with_ai(milestones: List[Dict[str, Any]], target_role_title: str, gap_skills: List[Dict[str, Any]]):
    try:
        skill_tasks = []
        for week in milestones:
            for task in week.get('tasks', []):
                if task.get('type') == 'skill':
                    skill_tasks.append(task)
        skill_tasks = sorted(skill_tasks, key=lambda t: {'high': 3, 'medium': 2, 'low': 1}.get(t.get('importance', 'medium'), 2), reverse=True)
        for task in skill_tasks[:3]:
            description = ai_service.generate_roadmap_task_descriptions(task.get('title', 'a key skill'), target_role_title)
            task['description'] = description
        return milestones
    except Exception:
        return milestones


def compute_roadmap_summary_stats(milestones: List[Dict[str, Any]]):
    total_tasks = 0
    skill_tasks = 0
    network_tasks = 0
    portfolio_tasks = 0
    checkpoint_tasks = 0
    total_estimated_hours = 0.0
    busiest_week_hours = 0.0
    weeks_with_most_tasks = 1

    for week in milestones or []:
        tasks = week.get('tasks', [])
        total_tasks += len(tasks)
        total_estimated_hours += sum(float(t.get('estimated_hours', 0) or 0) for t in tasks)
        if len(tasks) > weeks_with_most_tasks:
            weeks_with_most_tasks = week.get('week', weeks_with_most_tasks)
        week_hours = sum(float(t.get('estimated_hours', 0) or 0) for t in tasks)
        if week_hours > busiest_week_hours:
            busiest_week_hours = week_hours
        for task in tasks:
            task_type = task.get('type')
            if task_type == 'skill':
                skill_tasks += 1
            elif task_type == 'network':
                network_tasks += 1
            elif task_type == 'portfolio':
                portfolio_tasks += 1
            elif task_type == 'checkpoint':
                checkpoint_tasks += 1

    avg_hours_per_week = total_estimated_hours / 13 if milestones else 0.0

    return {
        'total_tasks': total_tasks,
        'skill_tasks_count': skill_tasks,
        'network_tasks_count': network_tasks,
        'portfolio_tasks_count': portfolio_tasks,
        'checkpoint_tasks_count': checkpoint_tasks,
        'total_estimated_hours': round(total_estimated_hours, 1),
        'avg_hours_per_week': round(avg_hours_per_week, 1),
        'weeks_with_most_tasks': weeks_with_most_tasks,
        'busiest_week_hours': round(busiest_week_hours, 1)
    }
