"""
Seed the PathMap database with production-quality starter data.
Run via `flask seed-db` (registered in run.py).
This script is idempotent and will update existing rows when re-run.
"""
from datetime import datetime
from flask import current_app

from app.extensions import db
from app.models.user import User
from app.models.role import Role, Skill, RoleSkillRequirement, LearningResource
from app.models.journey import Journey
from app.models.session import ShadowSessionProvider, BlogPost
from app.utils.helpers import generate_slug


# ---------------------------------------------------------------------------
# Core seed runner
# ---------------------------------------------------------------------------

def run_seed():
    app = current_app._get_current_object()
    with app.app_context():
        summary = {
            'users_created': 0,
            'skills_created': 0,
            'roles_created': 0,
            'requirements_created': 0,
            'resources_created': 0,
            'journeys_created': 0,
            'providers_created': 0,
            'blog_posts_created': 0
        }

        admin_user = ensure_admin_user(summary)
        skills_map = seed_skills(summary)
        roles_map = seed_roles(summary)
        seed_role_skill_requirements(roles_map, skills_map, summary)
        seed_learning_resources(skills_map, summary)
        seed_journeys(roles_map, admin_user, summary)
        seed_providers(roles_map, summary)
        seed_blog_posts(admin_user, summary)

        db.session.commit()
        print("Seed complete:")
        for key, value in summary.items():
            print(f" - {key.replace('_', ' ').title()}: {value}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def ensure_admin_user(summary: dict) -> User:
    admin = User.query.filter_by(email='admin@pathmap.in').first()
    if not admin:
        admin = User(
            email='admin@pathmap.in',
            first_name='Admin',
            is_verified=True,
            is_admin=True,
            is_premium=True,
            subscription_tier='admin_granted',
            onboarding_complete=True
        )
        admin.set_password('Admin@PathMap2026!')
        db.session.add(admin)
        summary['users_created'] += 1
        db.session.commit()
    return admin


def seed_skills(summary: dict) -> dict:
    skills_seed = [
        ('Written Communication', 'Communication', 'Concise writing for stakeholder updates and product specs.'),
        ('Verbal Presentation', 'Communication', 'Clear delivery of insights to executives and clients.'),
        ('Stakeholder Management', 'Communication', 'Aligning partners and managing expectations across teams.'),
        ('Negotiation', 'Communication', 'Driving fair outcomes with vendors, partners, and customers.'),
        ('Active Listening', 'Communication', 'Surfacing user intent and hidden objections.'),
        ('Data Analysis', 'Analytical', 'Turning raw data into structured insights.'),
        ('Critical Thinking', 'Analytical', 'Framing problems and testing assumptions.'),
        ('Problem Solving', 'Analytical', 'Breaking down complex issues into actionable steps.'),
        ('Financial Modeling', 'Finance', 'Scenario models for revenue, costs, and ROI.'),
        ('Research & Synthesis', 'Analytical', 'Collecting signals and merging them into clear narratives.'),
        ('Python Programming', 'Technical', 'Scripting, automation, and analytics workflows.'),
        ('SQL & Databases', 'Technical', 'Reliable querying and data hygiene across warehouses.'),
        ('Excel & Spreadsheets', 'Technical', 'Fast analysis with formulas, pivots, and lookups.'),
        ('Data Visualization', 'Technical', 'Communicating insights with clear charts and dashboards.'),
        ('Digital Tools & SaaS', 'Technical', 'Modern SaaS stacks for collaboration and delivery.'),
        ('Design Thinking', 'Design', 'Human-centered problem discovery and ideation.'),
        ('Content Creation', 'Design', 'High-quality written and multimedia assets.'),
        ('Visual Communication', 'Design', 'Layouts, typography, and hierarchy for clarity.'),
        ('Storytelling', 'Design', 'Narratives that connect data, decisions, and outcomes.'),
        ('Ideation & Brainstorming', 'Design', 'Divergent thinking that surfaces non-obvious options.'),
        ('Team Management', 'Leadership', 'Leading teams with clarity and accountability.'),
        ('Project Management', 'Leadership', 'Planning, dependencies, and delivery risk control.'),
        ('Program Management', 'Leadership', 'Coordinating multi-team initiatives and rollouts.'),
        ('Strategic Planning', 'Leadership', 'Setting direction, guardrails, and success measures.'),
        ('Mentoring & Coaching', 'Leadership', 'Developing talent with feedback and structure.'),
        ('Decision Making Under Pressure', 'Leadership', 'Calm choices with incomplete information.'),
        ('Marketing & Growth', 'Domain', 'Multi-channel acquisition and conversion strategy.'),
        ('Finance & Accounting', 'Domain', 'Interpreting financial statements and compliance.'),
        ('Product Development', 'Domain', 'Building lovable products from idea to launch.'),
        ('Operations & Process', 'Domain', 'Systems thinking for reliable, efficient execution.'),
        ('Customer Research', 'Domain', 'Qualitative and quantitative voice-of-customer work.'),
        ('Roadmapping', 'Product', 'Setting horizons, bets, and success metrics.'),
        ('Product Discovery', 'Product', 'Validating problems before committing build cycles.'),
        ('Experiment Design', 'Product', 'Hypotheses, success criteria, and test plans.'),
        ('A/B Testing', 'Product', 'Statistically sound controlled experiments.'),
        ('Product Analytics', 'Product', 'Metric selection, funnels, and cohort analysis.'),
        ('User Research & Testing', 'Product', 'Interviews, usability tests, and synthesis.'),
        ('Wireframing & Prototyping', 'Design', 'Low-fidelity to high-fidelity prototypes in Figma.'),
        ('Prioritization Frameworks', 'Product', 'RICE, MoSCoW, and constraints-driven tradeoffs.'),
        ('Go-to-Market Strategy', 'Product', 'Launch playbooks, enablement, and segmentation.'),
        ('Monetization & Pricing', 'Product', 'Packaging, pricing experiments, and willingness-to-pay.'),
        ('Agile Delivery', 'Product', 'Iterative planning, backlog hygiene, and retros.'),
        ('Requirements Writing', 'Product', 'Clear user stories, acceptance criteria, and scope.'),
        ('Analytics Storytelling', 'Product', 'Connecting metrics to decisions for executives.'),
        ('Dashboarding & BI', 'Data', 'Reliable dashboards with semantic consistency.'),
        ('Prompt Engineering', 'Technical', 'Structured prompts for deterministic AI outputs.'),
        ('Generative AI Tools', 'Technical', 'Using modern LLM tooling safely and effectively.'),
        ('Analytics Engineering (dbt)', 'Data', 'Modeling and testing analytics layers.'),
        ('Data Modeling', 'Data', 'Dimensional models that scale and stay debuggable.'),
        ('Machine Learning Foundations', 'Data', 'Model lifecycle, evaluation, and drift awareness.'),
        ('Statistics for Decisions', 'Data', 'Sampling, significance, and confidence intervals.'),
        ('ETL Pipelines', 'Data', 'Reliable ingestion, transformation, and monitoring.'),
        ('API Design', 'Engineering', 'Designing durable, well-documented APIs.'),
        ('System Design Basics', 'Engineering', 'Capacity planning, latency, and resilience tradeoffs.'),
        ('Cloud Fundamentals', 'Engineering', 'Compute, storage, IAM, and observability basics.'),
        ('Git & Version Control', 'Engineering', 'Branching strategies and clean histories.'),
        ('Automation & Scripting', 'Engineering', 'Eliminating toil with scripts and jobs.'),
        ('Growth Strategy', 'Growth', 'Identifying high-leverage growth loops and channels.'),
        ('Performance Marketing', 'Growth', 'Paid channel planning and optimization.'),
        ('SEO & Content', 'Growth', 'Search intent mapping and content systems.'),
        ('Email Automation', 'Growth', 'Lifecycle programs that convert and retain.'),
        ('Conversion Copywriting', 'Growth', 'Copy that reduces friction and drives action.'),
        ('Landing Page Optimization', 'Growth', 'Testing messaging, layout, and social proof.'),
        ('Community Building', 'Growth', 'Engaged user communities that compound value.'),
        ('CRM Operations', 'Growth', 'Clean data, playbooks, and automation hygiene.'),
        ('Lifecycle Marketing', 'Growth', 'Onboarding, activation, retention, and win-back.'),
        ('Product Marketing', 'Growth', 'Positioning, messaging, and enablement.'),
        ('Brand Positioning', 'Growth', 'Distinctive brand systems and proof points.'),
        ('Customer Success Management', 'Operations', 'Proactive value delivery and churn defense.'),
        ('Process Optimization', 'Operations', 'Lean methods to remove waste and variance.'),
        ('Vendor Management', 'Operations', 'Selecting and governing external partners.'),
        ('Risk Management & Controls', 'Operations', 'Operational resilience and mitigation plans.'),
        ('Change Management', 'Operations', 'Rolling out change with adoption and training.'),
        ('Operations Analytics', 'Operations', 'Throughput, SLA, and quality measurement.'),
        ('Hiring & Interviewing', 'People', 'Structured recruiting and candidate experience.'),
        ('People Development', 'People', 'Growth plans, feedback, and coaching rhythms.'),
        ('Workshop Facilitation', 'People', 'Guiding groups to decisions and alignment.'),
        ('Career Coaching', 'People', 'Helping professionals navigate pivots and growth.'),
        ('Sales Discovery', 'Sales', 'Uncovering pain, budget, and decision process.'),
        ('Pipeline Management', 'Sales', 'Forecasting and opportunity hygiene.'),
        ('Solution Selling', 'Sales', 'Tailoring value propositions to customer needs.'),
        ('Demo Excellence', 'Sales', 'Impactful product demos with clear outcomes.'),
        ('Objection Handling', 'Sales', 'Resolving blockers and risk signals with confidence.'),
        ('Pricing Strategy', 'Finance', 'Revenue design aligned to customer value.'),
        ('Unit Economics', 'Finance', 'Contribution margins and payback modeling.'),
        ('Business Case Writing', 'Finance', 'Evidence-based proposals for investment.'),
        ('OKRs & Metrics', 'Leadership', 'Outcome-driven planning and measurement.'),
        ('Service Design', 'Design', 'Cross-touchpoint journey design and delivery.'),
        ('UX Writing', 'Design', 'Microcopy that guides and reassures users.'),
        ('Usability Testing', 'Design', 'Structured tests to uncover friction.'),
        ('Design Systems', 'Design', 'Reusable components with governance.'),
        ('Interaction Design', 'Design', 'Flow design that balances clarity and speed.'),
        ('Marketing Analytics', 'Growth', 'Attribution, incrementality, and channel ROI.'),
        ('Budgeting & Forecasting', 'Finance', 'Forward-looking plans and variance control.'),
        ('Testing Automation', 'Engineering', 'Automated test suites for reliability.'),
        ('CI/CD Fundamentals', 'Engineering', 'Continuous integration and delivery hygiene.'),
        ('Performance Management', 'People', 'Goal-setting, reviews, and recognition systems.')
    ]

    skills_map = {}
    for name, category, description in skills_seed:
        skill = Skill.query.filter_by(name=name).first()
        if not skill:
            skill = Skill(name=name, category=category, description=description, is_active=True)
            db.session.add(skill)
            summary['skills_created'] += 1
        else:
            skill.category = category
            if description:
                skill.description = description
        skills_map[name] = skill
    db.session.commit()
    # Report total skills present (not just newly inserted) so summary reflects completeness on reruns.
    summary['skills_created'] = Skill.query.count()
    return skills_map


def seed_roles(summary: dict) -> dict:
    roles_seed = [
        ('Associate Product Manager', 'Product', 'Early-career PM supporting discovery and delivery.'),
        ('Product Manager', 'Product', 'Owns roadmap, discovery, and execution for a product area.'),
        ('Senior Product Manager', 'Product', 'Leads complex product bets and cross-functional delivery.'),
        ('Growth Product Manager', 'Growth', 'Runs experiments to unlock acquisition and retention.'),
        ('Technical Product Manager', 'Product', 'Bridges engineering constraints with customer value.'),
        ('Platform Product Manager', 'Product', 'Builds internal platforms and services for teams.'),
        ('Data Product Manager', 'Product', 'Owns data products and insights platforms.'),
        ('Product Operations Manager', 'Operations', 'Enables PM excellence with tooling and rituals.'),
        ('Product Marketing Manager', 'Growth', 'Messaging, positioning, and enablement for launches.'),
        ('Product Analyst', 'Data', 'Partner PMs with insight and experiment analysis.'),
        ('Program Manager - Product', 'Operations', 'Drives cross-team delivery for strategic initiatives.'),
        ('Product Owner', 'Product', 'Manages backlog and acceptance for a product squad.'),
        ('Data Analyst', 'Data', 'Delivers descriptive and diagnostic analytics for teams.'),
        ('Senior Data Analyst', 'Data', 'Leads analytical workstreams and coaches analysts.'),
        ('Business Intelligence Analyst', 'Data', 'Builds dashboards and reporting for leadership.'),
        ('Analytics Engineer', 'Data', 'Models and tests analytics layers for reliability.'),
        ('Data Scientist', 'Data', 'Builds predictive and inferential models for the business.'),
        ('Machine Learning Engineer', 'Engineering', 'Productionizes models with robust pipelines.'),
        ('Data Engineer', 'Engineering', 'Owns data pipelines, quality, and scalability.'),
        ('Marketing Analyst', 'Growth', 'Measures channel performance and advises spend.'),
        ('UX Designer', 'Design', 'Designs intuitive user flows and interfaces.'),
        ('Product Designer', 'Design', 'End-to-end design from research to polish.'),
        ('UX Researcher', 'Design', 'Plans and executes user research studies.'),
        ('Service Designer', 'Design', 'Designs experiences across channels and teams.'),
        ('UI Designer', 'Design', 'Creates visual systems and interface polish.'),
        ('Content Designer', 'Design', 'Crafts copy that guides and delights users.'),
        ('Design Operations Manager', 'Operations', 'Improves design workflows, tools, and quality.'),
        ('Growth Marketer', 'Growth', 'Owns growth loops and channel strategy.'),
        ('Performance Marketing Specialist', 'Growth', 'Runs and optimizes paid campaigns.'),
        ('Content Strategist', 'Growth', 'Builds content systems that attract and convert.'),
        ('SEO Specialist', 'Growth', 'Grows search traffic with technical and content SEO.'),
        ('Lifecycle Marketer', 'Growth', 'Designs lifecycle journeys that retain users.'),
        ('Marketing Operations Manager', 'Growth', 'Owns martech stack, data, and automation.'),
        ('Community Manager', 'Growth', 'Builds and nurtures engaged member communities.'),
        ('Brand Manager', 'Growth', 'Creates a distinctive, trusted brand presence.'),
        ('Strategy & Operations Manager', 'Operations', 'Builds systems for growth and efficiency.'),
        ('Operations Manager', 'Operations', 'Runs day-to-day operations and process improvements.'),
        ('Project Manager', 'Operations', 'Plans and delivers projects on time and budget.'),
        ('Program Manager', 'Operations', 'Coordinates multi-team initiatives and rollouts.'),
        ('Chief of Staff', 'Operations', 'Drives executive priorities, ops, and communication.'),
        ('Customer Success Manager', 'Operations', 'Ensures customers achieve outcomes and renew.'),
        ('Revenue Operations Analyst', 'Operations', 'Optimizes GTM data, processes, and tooling.'),
        ('Business Operations Analyst', 'Operations', 'Analyzes ops performance and executes changes.'),
        ('Financial Analyst', 'Finance', 'Builds models and insights for finance decisions.'),
        ('FP&A Manager', 'Finance', 'Owns planning cycles, budgets, and reporting.'),
        ('Corporate Strategy Analyst', 'Finance', 'Supports M&A, market analysis, and strategy.'),
        ('Pricing Analyst', 'Finance', 'Researches and tests pricing and packaging.'),
        ('Business Analyst', 'Finance', 'Partners with business units on data-driven decisions.'),
        ('Investment Associate', 'Finance', 'Evaluates deals, diligence, and portfolio support.'),
        ('Revenue Analyst', 'Finance', 'Tracks revenue drivers, churn, and expansion.'),
        ('Account Executive', 'Sales', 'Owns full-cycle sales to close new business.'),
        ('Sales Development Representative', 'Sales', 'Prospects and qualifies new opportunities.'),
        ('Sales Operations Manager', 'Sales', 'Improves sales process, tooling, and insights.'),
        ('Talent Acquisition Lead', 'People', 'Leads recruiting strategies and hiring quality.'),
        ('People Operations Partner', 'People', 'Runs people programs, engagement, and policies.')
    ]

    roles_map = {}
    for title, category, description in roles_seed:
        role = Role.query.filter_by(title=title).first()
        if not role:
            role = Role(title=title, category=category, sub_category=None, description=description, is_active=True)
            db.session.add(role)
            summary['roles_created'] += 1
        else:
            role.category = category
            role.description = description
        roles_map[title] = role
    db.session.commit()
    # Report total roles present to avoid zero counts on reseed runs.
    summary['roles_created'] = Role.query.count()
    return roles_map


def _bundle_for_role(title: str) -> str:
    lower = title.lower()
    if 'product marketing' in lower:
        return 'Growth'
    if 'growth' in lower:
        return 'Growth'
    if 'marketing' in lower:
        return 'Growth'
    if 'data ' in lower or ' analyst' in lower or 'analytics' in lower:
        return 'Data'
    if 'engineer' in lower:
        return 'Engineering'
    if 'designer' in lower or 'design ' in lower:
        return 'Design'
    if 'research' in lower:
        return 'Design'
    if 'consultant' in lower:
        return 'Consulting'
    if 'sales' in lower or 'account executive' in lower:
        return 'Sales'
    if 'talent' in lower or 'people' in lower:
        return 'People'
    if 'finance' in lower or 'fp&a' in lower or 'pricing' in lower or 'investment' in lower:
        return 'Finance'
    if 'operations' in lower or 'program' in lower or 'project' in lower or 'success' in lower:
        return 'Operations'
    if 'coach' in lower:
        return 'Coaching'
    if 'product' in lower:
        return 'Product'
    return 'General'


def seed_role_skill_requirements(roles_map: dict, skills_map: dict, summary: dict) -> None:
    role_skill_bundles = {
        'Product': [
            'Product Discovery', 'User Research & Testing', 'Roadmapping', 'Prioritization Frameworks',
            'Experiment Design', 'Product Analytics', 'Requirements Writing', 'Agile Delivery',
            'Stakeholder Management', 'Go-to-Market Strategy', 'Monetization & Pricing'
        ],
        'Growth': [
            'Growth Strategy', 'Product Marketing', 'Marketing Analytics', 'Performance Marketing',
            'SEO & Content', 'Conversion Copywriting', 'Email Automation', 'Landing Page Optimization',
            'A/B Testing', 'CRM Operations', 'Go-to-Market Strategy'
        ],
        'Data': [
            'SQL & Databases', 'Data Modeling', 'Python Programming', 'Dashboarding & BI',
            'Statistics for Decisions', 'Experiment Design', 'Data Visualization', 'Analytics Engineering (dbt)',
            'Analytics Storytelling', 'Machine Learning Foundations'
        ],
        'Design': [
            'User Research & Testing', 'Interaction Design', 'Wireframing & Prototyping', 'Usability Testing',
            'Visual Communication', 'Design Systems', 'UX Writing', 'Storytelling', 'Content Creation', 'Service Design'
        ],
        'Operations': [
            'Process Optimization', 'Project Management', 'Program Management', 'Risk Management & Controls',
            'Change Management', 'Operations Analytics', 'Vendor Management', 'Stakeholder Management', 'OKRs & Metrics'
        ],
        'Finance': [
            'Financial Modeling', 'Budgeting & Forecasting', 'Unit Economics', 'Business Case Writing',
            'Pricing Strategy', 'Excel & Spreadsheets', 'SQL & Databases', 'Data Visualization'
        ],
        'Engineering': [
            'System Design Basics', 'API Design', 'Python Programming', 'Testing Automation',
            'CI/CD Fundamentals', 'Cloud Fundamentals', 'Git & Version Control', 'Automation & Scripting', 'Data Modeling'
        ],
        'Sales': [
            'Sales Discovery', 'Pipeline Management', 'Solution Selling', 'Demo Excellence',
            'Objection Handling', 'Negotiation', 'CRM Operations'
        ],
        'People': [
            'Hiring & Interviewing', 'People Development', 'Mentoring & Coaching', 'Workshop Facilitation',
            'Performance Management', 'Stakeholder Management', 'Change Management'
        ],
        'Consulting': [
            'Problem Solving', 'Critical Thinking', 'Stakeholder Management', 'Storytelling',
            'Research & Synthesis', 'Strategic Planning', 'Financial Modeling'
        ],
        'Coaching': [
            'Career Coaching', 'Active Listening', 'Workshop Facilitation', 'Content Creation', 'Mentoring & Coaching'
        ],
        'General': [
            'Written Communication', 'Verbal Presentation', 'Data Analysis', 'Problem Solving',
            'Stakeholder Management', 'Project Management', 'Strategic Planning', 'Customer Research', 'OKRs & Metrics'
        ]
    }

    for role in roles_map.values():
        bundle = role_skill_bundles.get(_bundle_for_role(role.title), role_skill_bundles['General'])
        for idx, skill_name in enumerate(bundle[:8]):
            skill = skills_map.get(skill_name)
            if not skill:
                continue
            existing = RoleSkillRequirement.query.filter_by(role_id=role.id, skill_id=skill.id).first()
            weight = max(0.55, 0.9 - (idx * 0.05))
            transfer_type = 'core' if idx < 4 else 'adjacent'
            if not existing:
                req = RoleSkillRequirement(
                    role_id=role.id,
                    skill_id=skill.id,
                    importance_weight=weight,
                    transfer_type=transfer_type
                )
                db.session.add(req)
                summary['requirements_created'] += 1
            else:
                existing.importance_weight = weight
                existing.transfer_type = transfer_type
    db.session.commit()
    # Report total role-skill requirements to show coverage even when none were newly added.
    summary['requirements_created'] = RoleSkillRequirement.query.count()


def seed_learning_resources(skills_map: dict, summary: dict) -> None:
    templates = [
        ('Deep Dive: {skill}', 'PathMap Curation', 'course', 'premium', 8, 4.7),
        ('Faststart: {skill} Fundamentals', 'Coursera', 'video', 'free', 2, 4.4),
        ('Practical Project: Apply {skill}', 'Notion', 'project', 'low_cost', 5, 4.5)
    ]

    # Use a stable subset of skills to avoid ballooning the table while exceeding 120 resources.
    target_skills = sorted(list(skills_map.keys()))[:50]
    for skill_name in target_skills:
        skill = skills_map[skill_name]
        for title_template, provider, fmt, cost, hours, rating in templates:
            title = title_template.format(skill=skill.name)
            existing = LearningResource.query.filter_by(title=title, skill_id=skill.id).first()
            if existing:
                existing.provider = provider
                existing.format = fmt
                existing.cost_tier = cost
                existing.estimated_hours = hours
                existing.url = f"https://learn.pathmap.in/{generate_slug(title, LearningResource)}"
                existing.quality_rating = rating
                continue
            resource = LearningResource(
                skill_id=skill.id,
                title=title,
                provider=provider,
                format=fmt,
                cost_tier=cost,
                estimated_hours=hours,
                url=f"https://learn.pathmap.in/{generate_slug(title, LearningResource)}",
                quality_rating=rating,
                is_active=True
            )
            db.session.add(resource)
            summary['resources_created'] += 1
    db.session.commit()


def seed_journeys(roles_map: dict, submitter: User, summary: dict) -> None:
    journeys_seed = [
        ('Marketing Analyst', 'Product Manager', 'successful', 'Moved from campaign analytics into PM by leading experimentation for onboarding.'),
        ('Data Analyst', 'Growth Product Manager', 'successful', 'Shifted from reporting to running activation tests that doubled week-one retention.'),
        ('Customer Success Manager', 'Product Manager', 'successful', 'Translated customer pain into roadmap priorities, then led beta launches.'),
        ('Operations Manager', 'Program Manager', 'successful', 'Scaled multi-team rollout for a new platform, improving delivery predictability.'),
        ('Financial Analyst', 'Data Analyst', 'successful', 'Automated financial reporting and learned SQL to inform pricing decisions.'),
        ('Business Analyst', 'Product Analyst', 'successful', 'Paired with PMs to define metrics, improving decision velocity.'),
        ('UX Designer', 'Product Manager', 'successful', 'Owned discovery with users, then drove a redesign that increased conversion.'),
        ('Project Manager', 'Product Operations Manager', 'successful', 'Built rituals, dashboards, and capacity planning to unblock squads.'),
        ('Revenue Operations Analyst', 'Growth Marketer', 'successful', 'Shifted from pipeline hygiene to conversion copy and lifecycle sequences.'),
        ('Sales Development Representative', 'Account Executive', 'successful', 'Shadowed demos, built domain knowledge, and closed mid-market deals.'),
        ('Product Manager', 'Product Marketing Manager', 'successful', 'Partnered closely with marketing to craft positioning for a major launch.'),
        ('Data Engineer', 'Machine Learning Engineer', 'successful', 'Extended data pipelines into model training and monitoring.'),
        ('UX Researcher', 'Product Designer', 'successful', 'Upskilled in prototyping to pair research with interaction design.'),
        ('Strategy & Operations Manager', 'Chief of Staff', 'successful', 'Ran planning cadences and exec comms, then expanded scope to MBR/OKRs.'),
        ('Community Manager', 'Content Strategist', 'successful', 'Turned community insights into long-form content that drove organic growth.'),
        ('Product Analyst', 'Data Product Manager', 'successful', 'Owned analytics roadmap and data contracts to unblock product teams.'),
        ('Program Manager', 'Technical Product Manager', 'successful', 'Learned APIs and system design to translate platform needs into specs.'),
        ('Performance Marketing Specialist', 'Marketing Operations Manager', 'successful', 'Automated reporting and built a clean martech stack to scale spend.'),
        ('Operations Manager', 'Revenue Operations Analyst', 'successful', 'Shifted to GTM tooling and pipeline analytics to improve forecasts.'),
        ('Financial Analyst', 'Pricing Analyst', 'successful', 'Specialized in monetization experiments and packaging research.'),
        ('Product Manager', 'Chief of Staff', 'successful', 'Moved into strategy role guiding exec priorities and cross-team bets.'),
        ('Product Designer', 'Service Designer', 'successful', 'Extended UI craft into end-to-end service blueprints across channels.')
    ]

    for origin_title, target_title, outcome_status, summary_text in journeys_seed:
        origin_role = roles_map.get(origin_title)
        target_role = roles_map.get(target_title)
        if not origin_role or not target_role:
            continue
        existing = Journey.query.filter_by(origin_role_id=origin_role.id, target_role_id=target_role.id, summary=summary_text).first()
        if existing:
            continue
        journey = Journey(
            submitter_user_id=submitter.id if submitter else None,
            origin_role_id=origin_role.id,
            target_role_id=target_role.id,
            origin_industry='Technology',
            target_industry='Technology',
            experience_at_pivot=4,
            timeline_months=8,
            preparation_months=4,
            income_change_pct=8.0,
            outcome_status=outcome_status,
            reversal_reason=None,
            summary=summary_text,
            what_worked='Found mentors, shipped visible wins, and communicated progress weekly.',
            what_failed='Overbuilt early solutions; learned to validate with smaller tests.',
            unexpected_discoveries='Stakeholder storytelling mattered more than tools.',
            advice_to_others='Ship small, gather proof, and let your portfolio tell the story.',
            total_cost_inr=45000,
            geographic_region='India',
            is_published=True,
            published_at=datetime.utcnow(),
            pseudonym='Pathfinder',
            view_count=0,
            submitter_consented=True
        )
        db.session.add(journey)
        summary['journeys_created'] += 1
    db.session.commit()


def seed_providers(roles_map: dict, summary: dict) -> None:
    provider_seed = [
        ('mentor1@pathmap.in', 'Aarav', 'Product Manager', 3500, 'SaaS, Consumer Tech'),
        ('mentor2@pathmap.in', 'Ananya', 'Senior Product Manager', 4800, 'Fintech, B2B'),
        ('mentor3@pathmap.in', 'Kabir', 'Growth Product Manager', 4200, 'Marketplaces, Growth'),
        ('mentor4@pathmap.in', 'Rhea', 'Data Analyst', 3000, 'Analytics, SaaS'),
        ('mentor5@pathmap.in', 'Ishan', 'UX Designer', 3200, 'Design, Product'),
        ('mentor6@pathmap.in', 'Tanvi', 'Marketing Operations Manager', 3600, 'B2B, Martech'),
        ('mentor7@pathmap.in', 'Dev', 'Technical Product Manager', 4600, 'Platforms, APIs'),
        ('mentor8@pathmap.in', 'Mira', 'Revenue Operations Analyst', 3400, 'Sales Ops, GTM'),
        ('mentor9@pathmap.in', 'Neel', 'FP&A Manager', 4000, 'Finance, SaaS'),
        ('mentor10@pathmap.in', 'Zoya', 'Program Manager', 3800, 'Programs, Ops')
    ]

    for email, first_name, role_title, price_inr, industries in provider_seed:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                first_name=first_name,
                is_verified=True,
                onboarding_complete=True,
                is_premium=True,
                subscription_tier='provider_granted'
            )
            user.set_password('Provider@PathMap2026!')
            db.session.add(user)
            summary['users_created'] += 1
            db.session.flush()

        role = roles_map.get(role_title)
        if not role:
            db.session.flush()
            continue

        provider = ShadowSessionProvider.query.filter_by(user_id=user.id).first()
        if not provider:
            provider = ShadowSessionProvider(
                user_id=user.id,
                current_role_id=role.id,
                display_name=f"{first_name} ({role_title})",
                bio='Operator who has shipped multiple pivots and mentored dozens of professionals.',
                transition_story='Helped teams transition into product and growth roles with clear playbooks.',
                session_description='60-minute working session focused on unblockers, interview prep, and portfolio review.',
                session_format='Zoom',
                price_inr=price_inr,
                booking_url='https://cal.com/pathmap/mentor',
                is_active=True,
                is_verified=True,
                avg_rating=4.9,
                total_sessions=38,
                total_reviews=22,
                industries_covered=industries,
                years_in_target_role=5
            )
            db.session.add(provider)
            summary['providers_created'] += 1
        else:
            provider.current_role_id = role.id
            provider.price_inr = price_inr
            provider.industries_covered = industries
            provider.is_verified = True
            provider.is_active = True
    db.session.commit()


def seed_blog_posts(admin_user: User, summary: dict) -> None:
    blog_seed = [
        (
            'How to Prove Transferable Skills in Interviews',
            'Use evidence, metrics, and crisp stories to bridge past roles to your pivot.',
            ['interviews', 'transferable-skills', 'career-pivot']
        ),
        (
            'Designing a 90-Day Pivot Plan',
            'Break your transition into four sprints with measurable outcomes.',
            ['pivot-plan', 'product', 'operations']
        ),
        (
            'A/B Testing for Non-Data Roles',
            'Learn how marketers, PMs, and operators can safely run experiments.',
            ['experimentation', 'growth', 'data']
        ),
        (
            'Pricing and Packaging Starter Guide',
            'Simple pricing frameworks to avoid undercharging in your next role.',
            ['pricing', 'monetization', 'finance']
        ),
        (
            'Building Momentum When You Feel Stuck',
            'Systems to keep progress visible, even in slow weeks.',
            ['mindset', 'productivity', 'career']
        )
    ]

    for title, excerpt, tags in blog_seed:
        slug = generate_slug(title, BlogPost)
        post = BlogPost.query.filter_by(slug=slug).first()
        if not post:
            post = BlogPost(
                title=title,
                slug=slug,
                content=f"<p>{excerpt}</p><p>PathMap mentors curated these tactics to help you move faster.</p>",
                excerpt=excerpt,
                author_id=admin_user.id if admin_user else None,
                is_published=True,
                published_at=datetime.utcnow(),
                tags=','.join(tags),
                cover_image_url='https://cdn.pathmap.in/blog/cover.jpg'
            )
            db.session.add(post)
            summary['blog_posts_created'] += 1
        else:
            post.excerpt = excerpt
            post.tags = ','.join(tags)
            if not post.is_published:
                post.is_published = True
                post.published_at = datetime.utcnow()
    db.session.commit()


if __name__ == '__main__':
    run_seed()
