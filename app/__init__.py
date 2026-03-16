import os
from flask import Flask, render_template
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from .config import config
from .extensions import db, migrate, login_manager, mail, csrf, limiter
from .utils.context_processors import inject_assessment_progress, inject_progress_streak, inject_admin_badges
from .utils.markdown_renderer import is_markdown as detect_markdown, markdown_to_html


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.dashboard import dashboard_bp
    from .routes.journeys import journeys_bp
    from .routes.assessment import assessment_bp
    from .routes.profile import profile_bp
    from .routes.admin import admin_bp
    from .routes.payment import payment_bp
    from .routes.onboarding import onboarding_bp
    from .routes.analysis import analysis_bp
    from .routes.planner import planner_bp
    from .routes.progress import progress_bp
    from .routes.sessions import sessions_bp
    from .routes.resources import resources_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(journeys_bp, url_prefix='/journeys')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(assessment_bp, url_prefix='/assessment')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
    app.register_blueprint(analysis_bp, url_prefix='/skill-transfer')
    app.register_blueprint(planner_bp, url_prefix='/pivot-planner')
    app.register_blueprint(progress_bp, url_prefix='/progress')
    app.register_blueprint(sessions_bp, url_prefix='/shadow-sessions')
    app.register_blueprint(resources_bp, url_prefix='/resources')

    from .utils.helpers import format_inr, time_ago, truncate_text
    app.jinja_env.filters['format_inr'] = format_inr
    app.jinja_env.filters['time_ago'] = time_ago
    app.jinja_env.filters['truncate_text'] = truncate_text
    app.jinja_env.filters['markdown'] = lambda text: markdown_to_html(text, trusted_source=False)
    app.jinja_env.filters['markdown_trusted'] = lambda text: markdown_to_html(text, trusted_source=True)
    app.jinja_env.filters['markdown_force'] = lambda text: markdown_to_html(text, trusted_source=False, force_markdown=True)
    app.jinja_env.tests['is_markdown'] = detect_markdown

    app.context_processor(inject_assessment_progress)
    app.context_processor(inject_progress_streak)
    app.context_processor(inject_admin_badges)

    # Import models so Flask-Migrate detects them
    from .models import user  # noqa: F401
    from .models import journey  # noqa: F401
    from .models import session  # noqa: F401
    from .models import role  # noqa: F401
    from .models import assessment  # noqa: F401
    from .models import roadmap  # noqa: F401
    from .models import analysis  # noqa: F401
    from .models import payment  # noqa: F401

    from .models.user import User
    from .models.assessment import UserAssessment
    from .models.roadmap import PivotRoadmap, ProgressEntry
    from .models.journey import Journey, JourneyView
    from .models.role import Role, Skill, RoleSkillRequirement, LearningResource
    from .models.analysis import SkillTransferAnalysis
    from .models.session import ShadowSessionProvider, SessionReview, SessionBooking, ProviderApplication, ResourceBookmark
    from .models.payment import SubscriptionPayment, AdminAuditLog
    from .services.roadmap_gen import generate_roadmap
    from .services.pdf_service import generate_decision_pdf

    @app.shell_context_processor
    def shell_context():
        return {
            'db': db,
            'User': User,
            'UserAssessment': UserAssessment,
            'PivotRoadmap': PivotRoadmap,
            'ProgressEntry': ProgressEntry,
            'Journey': Journey,
            'JourneyView': JourneyView,
            'Role': Role,
            'Skill': Skill,
            'RoleSkillRequirement': RoleSkillRequirement,
            'LearningResource': LearningResource,
            'SkillTransferAnalysis': SkillTransferAnalysis,
            'ShadowSessionProvider': ShadowSessionProvider,
            'SessionReview': SessionReview,
            'SessionBooking': SessionBooking,
            'ProviderApplication': ProviderApplication,
            'ResourceBookmark': ResourceBookmark,
            'SubscriptionPayment': SubscriptionPayment,
            'AdminAuditLog': AdminAuditLog,
            'generate_roadmap': generate_roadmap,
            'generate_decision_pdf': generate_decision_pdf
        }

    ensure_database(app)

    # Register custom error handlers
    from .routes.errors import register_error_handlers
    register_error_handlers(app)

    @app.cli.command('drop-db')
    def drop_database():
        """Drop all database tables. Use only in development."""
        db.drop_all()
        print("All database tables dropped.")

    @app.cli.command('create-db')
    def create_database():
        """Create all database tables."""
        db.create_all()
        print("All database tables created.")

    return app


def ensure_database(app):
    """Ensure the database and tables exist on first run."""
    with app.app_context():
        engine = db.get_engine()

        if engine.url.drivername.startswith('sqlite'):
            db_path = engine.url.database
            if db_path:
                db_dir = os.path.dirname(db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)

        try:
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
        except OperationalError as exc:
            app.logger.warning('Database inspection failed; creating tables: %s', exc)
            existing_tables = []

        if not existing_tables:
            db.create_all()
