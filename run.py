import os
from dotenv import load_dotenv
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.role import Role, Skill, RoleSkillRequirement, LearningResource
from app.models.assessment import UserAssessment
from app.models.analysis import SkillTransferAnalysis
from app.models.journey import Journey
from app.models.roadmap import PivotRoadmap, ProgressEntry
from app.models.session import ShadowSessionProvider, SessionReview, SessionBooking, ProviderApplication, ResourceBookmark, BlogPost
from app.models.payment import SubscriptionPayment, AdminAuditLog

load_dotenv()

app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Skill': Skill,
        'RoleSkillRequirement': RoleSkillRequirement,
        'LearningResource': LearningResource,
        'UserAssessment': UserAssessment,
        'SkillTransferAnalysis': SkillTransferAnalysis,
        'Journey': Journey,
        'PivotRoadmap': PivotRoadmap,
        'ProgressEntry': ProgressEntry,
        'ShadowSessionProvider': ShadowSessionProvider,
        'SessionReview': SessionReview,
        'SessionBooking': SessionBooking,
        'ProviderApplication': ProviderApplication,
        'ResourceBookmark': ResourceBookmark,
        'SubscriptionPayment': SubscriptionPayment,
        'AdminAuditLog': AdminAuditLog,
        'BlogPost': BlogPost
    }


@app.cli.command('seed-db')
def seed_database():
    """Seed the database with production-quality starter data."""
    from seed_data.seed import run_seed
    run_seed()


@app.cli.command('create-admin')
def create_admin():
    """Create the default admin user if missing."""
    existing = User.query.filter_by(email='admin@pathmap.in').first()
    if existing:
        print('Admin user already exists.')
        return
    admin = User(
        email='admin@pathmap.in',
        first_name='Admin',
        is_verified=True,
        is_admin=True,
        is_premium=True,
        subscription_tier='admin_granted',
        onboarding_complete=True
    )
    admin.set_password('Admin@PathMap2024!')
    db.session.add(admin)
    db.session.commit()
    print('Admin user created: admin@pathmap.in / Admin@PathMap2024!')


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
