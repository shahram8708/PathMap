from datetime import datetime
from ..extensions import db


class Journey(db.Model):
    __tablename__ = 'journeys'

    id = db.Column(db.Integer, primary_key=True)
    submitter_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    origin_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    target_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    origin_industry = db.Column(db.String(100), nullable=True)
    target_industry = db.Column(db.String(100), nullable=True)
    experience_at_pivot = db.Column(db.Integer, nullable=True)
    timeline_months = db.Column(db.Integer, nullable=True)
    preparation_months = db.Column(db.Integer, nullable=True)
    income_change_pct = db.Column(db.Float, nullable=True)
    outcome_status = db.Column(db.String(50), nullable=False)
    reversal_reason = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=False)
    what_worked = db.Column(db.Text, nullable=False)
    what_failed = db.Column(db.Text, nullable=False)
    unexpected_discoveries = db.Column(db.Text, nullable=False)
    advice_to_others = db.Column(db.Text, nullable=False)
    total_cost_inr = db.Column(db.Float, nullable=True)
    geographic_region = db.Column(db.String(100), nullable=True)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    pseudonym = db.Column(db.String(100), nullable=True)
    view_count = db.Column(db.Integer, default=0, nullable=False)
    submitter_consented = db.Column(db.Boolean, default=False, nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)

    origin_role = db.relationship('Role', foreign_keys=[origin_role_id])
    target_role = db.relationship('Role', foreign_keys=[target_role_id])
    submitter = db.relationship('User', backref='submitted_journeys')

    def __repr__(self):
        return f"<Journey {self.id} {self.outcome_status}>"


class JourneyView(db.Model):
    __tablename__ = 'journey_views'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    journey_id = db.Column(db.Integer, db.ForeignKey('journeys.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    view_month = db.Column(db.Integer, nullable=False)
    view_year = db.Column(db.Integer, nullable=False)

    journey = db.relationship('Journey', backref=db.backref('journey_views', lazy='dynamic'))

    __table_args__ = (
        db.Index('ix_journey_views_user_month_year', 'user_id', 'view_month', 'view_year'),
    )

    def __repr__(self):
        return f"<JourneyView user={self.user_id} journey={self.journey_id} {self.view_month}/{self.view_year}>"
