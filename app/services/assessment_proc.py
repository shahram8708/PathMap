from collections import Counter
from datetime import datetime
import re


SKILL_CATEGORIES = {
    'Communication': [
        'Written Communication',
        'Verbal Presentation',
        'Stakeholder Management',
        'Negotiation',
        'Active Listening'
    ],
    'Analytical': [
        'Data Analysis',
        'Critical Thinking',
        'Problem Solving',
        'Financial Modeling',
        'Research & Synthesis'
    ],
    'Technical': [
        'Python Programming',
        'SQL & Databases',
        'Excel & Spreadsheets',
        'Data Visualization',
        'Digital Tools & SaaS'
    ],
    'Creative': [
        'Design Thinking',
        'Content Creation',
        'Visual Communication',
        'Storytelling',
        'Ideation & Brainstorming'
    ],
    'Leadership': [
        'Team Management',
        'Project Management',
        'Strategic Planning',
        'Mentoring & Coaching',
        'Decision Making Under Pressure'
    ],
    'Domain': [
        'Marketing & Growth',
        'Finance & Accounting',
        'Product Development',
        'Operations & Process',
        'Customer Research'
    ]
}

_WORK_VALUE_PRIORITY = [
    'autonomy',
    'impact',
    'learning',
    'creativity',
    'flexibility',
    'collaboration',
    'stability',
    'income',
    'prestige',
    'social'
]

_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'from', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does',
    'did', 'will', 'would', 'could', 'should', 'may', 'might', 'i', 'my', 'me', 'we', 'our',
    'you', 'your', 'it', 'its', 'this', 'that', 'which', 'who', 'what', 'when', 'where',
    'how', 'not', 'no', 'so', 'as', 'if', 'more', 'most', 'can', 'also', 'just', 'very',
    'really', 'want', 'like', 'work', 'working'
}


def compute_values_profile(values_ratings_dict: dict) -> dict:
    sorted_items = sorted(
        values_ratings_dict.items(),
        key=lambda item: (
            -item[1],
            _WORK_VALUE_PRIORITY.index(item[0]) if item[0] in _WORK_VALUE_PRIORITY else len(_WORK_VALUE_PRIORITY)
        )
    )
    top_5 = [name for name, _ in sorted_items[:5]]
    ranked = [name for name, _ in sorted_items]
    return {
        'top_5': top_5,
        'scores': values_ratings_dict,
        'all_values_ranked': ranked
    }


def compute_workstyle_profile(responses_dict: dict) -> dict:
    question_dimensions = {
        'q1': 'execution_strategy', 'q2': 'execution_strategy', 'q3': 'execution_strategy',
        'q4': 'collaboration_independence', 'q5': 'collaboration_independence', 'q6': 'collaboration_independence',
        'q7': 'detail_bigpicture', 'q8': 'detail_bigpicture', 'q9': 'detail_bigpicture',
        'q10': 'structured_adaptive', 'q11': 'structured_adaptive', 'q12': 'structured_adaptive'
    }
    dimension_labels_map = {
        'execution_strategy': ('Execution-Focused', 'Strategy-Focused'),
        'collaboration_independence': ('Collaboration-Driven', 'Independent'),
        'detail_bigpicture': ('Detail-Oriented', 'Big-Picture Thinker'),
        'structured_adaptive': ('Structured', 'Adaptive')
    }

    dimension_scores = {key: [] for key in dimension_labels_map.keys()}
    for question_id, score in responses_dict.items():
        dimension = question_dimensions.get(question_id)
        if dimension:
            dimension_scores[dimension].append(int(score))

    averaged_scores = {}
    dimension_labels = {}
    secondary_candidates = []
    for dim, scores in dimension_scores.items():
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        averaged_scores[dim] = avg_score
        low_label, high_label = dimension_labels_map[dim]
        label = low_label if avg_score < 3.5 else high_label
        dimension_labels[dim] = label
        if 3.0 <= avg_score <= 4.0:
            secondary_candidates.append(label)

    dominant_style = ', '.join(dimension_labels.values())
    secondary_style = ', '.join(secondary_candidates)

    return {
        'dimension_scores': averaged_scores,
        'dimension_labels': dimension_labels,
        'dominant_style': dominant_style,
        'secondary_style': secondary_style
    }


def compute_skills_profile(ratings_dict: dict) -> dict:
    category_averages = {}
    for category, skills in SKILL_CATEGORIES.items():
        scores = [int(ratings_dict.get(_snake_key(skill), 0)) for skill in skills]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        category_averages[category] = avg_score
    return {
        'ratings': ratings_dict,
        'category_averages': category_averages
    }


def compute_vision_profile(vision_dict: dict) -> dict:
    combined_text = ' '.join([
        vision_dict.get('vision_day', ''),
        vision_dict.get('vision_impact', ''),
        vision_dict.get('vision_regret', '')
    ]).lower()
    tokens = re.findall(r"[a-zA-Z']+", combined_text)
    filtered = [word for word in tokens if word not in _STOPWORDS and len(word) >= 4]
    counts = Counter(filtered)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    themes = [word for word, _ in ranked[:5]]
    return {
        'vision_day': vision_dict.get('vision_day', ''),
        'vision_impact': vision_dict.get('vision_impact', ''),
        'vision_regret': vision_dict.get('vision_regret', ''),
        'vision_themes': themes
    }


def compute_full_profile_summary(assessment) -> dict:
    values = assessment.values_data or {}
    workstyle = assessment.workstyle_data or {}
    skills = assessment.skills_data or {}
    constraints = assessment.constraints_data or {}
    vision = assessment.vision_data or {}

    top_skill_category = ''
    bottom_skill_category = ''
    category_averages = skills.get('category_averages', {})
    if category_averages:
        sorted_categories = sorted(category_averages.items(), key=lambda item: item[1], reverse=True)
        top_skill_category = sorted_categories[0][0]
        bottom_skill_category = sorted(category_averages.items(), key=lambda item: item[1])[0][0]

    top_values = values.get('top_5', [])
    dominant_style = workstyle.get('dominant_style', '')
    vision_themes = vision.get('vision_themes', [])
    top_value_1 = top_values[0] if top_values else 'meaningful work'
    top_value_2 = top_values[1] if len(top_values) > 1 else 'growth'
    top_category_avg = category_averages.get(top_skill_category, 0.0)
    vision_theme_1 = vision_themes[0] if vision_themes else 'impact'

    rule_based_narrative = (
        f"You prioritize {top_value_1} and {top_value_2} in your work. "
        f"Your dominant professional style is {dominant_style}. "
        f"You bring strong {top_skill_category or 'core'} capabilities (rated {top_category_avg:.1f}/4.0) "
        f"and are seeking work that involves {vision_theme_1}."
    )

    return {
        'top_5_values': top_values,
        'dominant_style': dominant_style,
        'secondary_style': workstyle.get('secondary_style', ''),
        'dimension_scores': workstyle.get('dimension_scores', {}),
        'skill_category_averages': category_averages,
        'top_skill_category': top_skill_category,
        'bottom_skill_category': bottom_skill_category,
        'constraints': constraints,
        'vision_themes': vision_themes,
        'rule_based_narrative': rule_based_narrative,
        'ai_narrative': '',
        'generated_at': datetime.utcnow().isoformat()
    }


def get_work_values_list() -> list:
    return [
        {'key': 'autonomy', 'label': 'Autonomy', 'description': 'Freedom to decide how and when you work, with minimal micromanagement.'},
        {'key': 'creativity', 'label': 'Creativity', 'description': 'Ability to generate new ideas, design solutions, and express original thinking.'},
        {'key': 'stability', 'label': 'Stability', 'description': 'Predictable income, job security, and a low-risk professional environment.'},
        {'key': 'income', 'label': 'Financial Reward', 'description': 'High earning potential and financial growth as a measure of success.'},
        {'key': 'impact', 'label': 'Impact', 'description': 'Making a meaningful difference to individuals, communities, or the world.'},
        {'key': 'collaboration', 'label': 'Collaboration', 'description': 'Working closely with others, building relationships, and achieving as a team.'},
        {'key': 'learning', 'label': 'Continuous Learning', 'description': 'Regular opportunities to develop new skills and expand your knowledge.'},
        {'key': 'prestige', 'label': 'Prestige & Recognition', 'description': 'Being respected and recognized for your expertise and professional status.'},
        {'key': 'flexibility', 'label': 'Flexibility', 'description': 'Control over your schedule, location, and the structure of your workday.'},
        {'key': 'social', 'label': 'Social Connection', 'description': 'Feeling a sense of community, belonging, and human connection at work.'}
    ]


def get_workstyle_questions() -> list:
    return [
        {
            'id': 'q1',
            'dimension': 'execution_strategy',
            'left_label': 'I prefer executing defined tasks',
            'right_label': 'I prefer defining strategy and direction',
            'left_description': 'You enjoy implementing, building, and delivering.',
            'right_description': 'You enjoy setting direction, solving ambiguity, and leading thinking.'
        },
        {
            'id': 'q2',
            'dimension': 'execution_strategy',
            'left_label': 'I feel energized by shipping work quickly',
            'right_label': 'I feel energized by long-range planning',
            'left_description': 'Momentum and tangible outputs keep you motivated.',
            'right_description': 'You thrive when mapping scenarios and orchestrating plans.'
        },
        {
            'id': 'q3',
            'dimension': 'execution_strategy',
            'left_label': 'I like optimizing existing processes',
            'right_label': 'I like creating new blueprints',
            'left_description': 'You refine and improve systems that already exist.',
            'right_description': 'You design fresh approaches and architect solutions.'
        },
        {
            'id': 'q4',
            'dimension': 'collaboration_independence',
            'left_label': 'I prefer team-based decision making',
            'right_label': 'I prefer making independent calls',
            'left_description': 'You gain clarity through discussion and consensus.',
            'right_description': 'You move fastest when trusted to decide on your own.'
        },
        {
            'id': 'q5',
            'dimension': 'collaboration_independence',
            'left_label': 'I draw energy from group sessions',
            'right_label': 'I draw energy from focused solo time',
            'left_description': 'Collaboration fuels your creativity and drive.',
            'right_description': 'Deep, uninterrupted work helps you do your best thinking.'
        },
        {
            'id': 'q6',
            'dimension': 'collaboration_independence',
            'left_label': 'I seek feedback early and often',
            'right_label': 'I refine privately before sharing',
            'left_description': 'Input from others helps you iterate confidently.',
            'right_description': 'You prefer polishing ideas before inviting critique.'
        },
        {
            'id': 'q7',
            'dimension': 'detail_bigpicture',
            'left_label': 'I focus on precision and accuracy',
            'right_label': 'I focus on patterns and possibilities',
            'left_description': 'You enjoy catching edge cases and perfecting details.',
            'right_description': 'You look for trends and strategic opportunities.'
        },
        {
            'id': 'q8',
            'dimension': 'detail_bigpicture',
            'left_label': 'I document processes thoroughly',
            'right_label': 'I sketch vision and direction',
            'left_description': 'Clear documentation gives you confidence.',
            'right_description': 'You translate ideas into narratives and roadmaps.'
        },
        {
            'id': 'q9',
            'dimension': 'detail_bigpicture',
            'left_label': 'I measure success through exactness',
            'right_label': 'I measure success through momentum',
            'left_description': 'You value fidelity and adherence to standards.',
            'right_description': 'You value progress and trajectory over perfection.'
        },
        {
            'id': 'q10',
            'dimension': 'structured_adaptive',
            'left_label': 'I prefer clear processes and checklists',
            'right_label': 'I prefer flexible approaches',
            'left_description': 'Structure helps you deliver reliably.',
            'right_description': 'You like adjusting tactics as context shifts.'
        },
        {
            'id': 'q11',
            'dimension': 'structured_adaptive',
            'left_label': 'I plan ahead to reduce risk',
            'right_label': 'I adapt in the moment',
            'left_description': 'Preparation and sequencing calm you.',
            'right_description': 'You improvise confidently when plans change.'
        },
        {
            'id': 'q12',
            'dimension': 'structured_adaptive',
            'left_label': 'I like consistency day to day',
            'right_label': 'I like variety day to day',
            'left_description': 'Predictability lets you go deep.',
            'right_description': 'Novelty keeps you engaged and learning.'
        }
    ]


def get_skill_categories() -> list:
    category_meta = {
        'Communication': {'icon': 'bi-chat-dots', 'color': '#2E86C1'},
        'Analytical': {'icon': 'bi-graph-up', 'color': '#1E8449'},
        'Technical': {'icon': 'bi-code-slash', 'color': '#1A5276'},
        'Creative': {'icon': 'bi-palette', 'color': '#7D3C98'},
        'Leadership': {'icon': 'bi-people', 'color': '#D68910'},
        'Domain': {'icon': 'bi-briefcase', 'color': '#C0392B'}
    }
    skill_descriptions = {
        'Written Communication': 'Clarity in emails, reports, and documentation that drive action.',
        'Verbal Presentation': 'Presenting ideas with confidence to groups of any size.',
        'Stakeholder Management': 'Balancing needs and expectations across diverse stakeholders.',
        'Negotiation': 'Finding win-win terms in deals, offers, and scope discussions.',
        'Active Listening': 'Reading context, probing with questions, and responding thoughtfully.',
        'Data Analysis': 'Interpreting data sets to extract trends and actionable insights.',
        'Critical Thinking': 'Challenging assumptions and evaluating evidence objectively.',
        'Problem Solving': 'Diagnosing root causes and designing practical solutions.',
        'Financial Modeling': 'Building models to forecast revenue, cost, and profitability.',
        'Research & Synthesis': 'Gathering inputs and distilling them into clear recommendations.',
        'Python Programming': 'Writing clean, maintainable Python for automation or analysis.',
        'SQL & Databases': 'Querying and structuring data for reliability and scale.',
        'Excel & Spreadsheets': 'Building spreadsheet models with formulas, pivots, and checks.',
        'Data Visualization': 'Turning data into clear charts and narratives for decision makers.',
        'Digital Tools & SaaS': 'Adopting and integrating modern SaaS tools efficiently.',
        'Design Thinking': 'Human-centered approach to discover, ideate, prototype, and test.',
        'Content Creation': 'Producing engaging written, audio, or video content.',
        'Visual Communication': 'Communicating ideas through visuals, layouts, and hierarchy.',
        'Storytelling': 'Crafting narratives that move audiences to understand or act.',
        'Ideation & Brainstorming': 'Generating diverse concepts and pushing beyond first ideas.',
        'Team Management': 'Setting direction, coaching, and enabling high team performance.',
        'Project Management': 'Scoping, sequencing, and delivering projects on time.',
        'Strategic Planning': 'Mapping long-range objectives, bets, and resource allocation.',
        'Mentoring & Coaching': 'Developing people through feedback and structured guidance.',
        'Decision Making Under Pressure': 'Choosing confidently when stakes and ambiguity are high.',
        'Marketing & Growth': 'Designing campaigns and funnels that drive acquisition and retention.',
        'Finance & Accounting': 'Managing budgets, compliance, and financial reporting accuracy.',
        'Product Development': 'Defining requirements and guiding products from idea to launch.',
        'Operations & Process': 'Designing processes that improve reliability and efficiency.',
        'Customer Research': 'Interviewing users and translating insights into action.'
    }

    categories = []
    for category, skills in SKILL_CATEGORIES.items():
        meta = category_meta.get(category, {'icon': 'bi-circle', 'color': '#1A5276'})
        skill_items = []
        for skill in skills:
            key = _snake_key(skill)
            skill_items.append({
                'key': key,
                'label': skill,
                'description': skill_descriptions.get(skill, 'Core capability for this domain.')
            })
        categories.append({
            'category_name': category,
            'icon': meta['icon'],
            'color': meta['color'],
            'skills': skill_items
        })
    return categories


def _snake_key(name: str) -> str:
    name = name.replace('&', 'and').replace('/', ' ').replace('-', ' ')
    name = re.sub(r'[^A-Za-z0-9 ]+', '', name)
    return '_'.join(name.lower().split())
