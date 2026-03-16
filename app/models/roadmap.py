from datetime import datetime, date
from ..extensions import db


class PivotRoadmap(db.Model):
    __tablename__ = 'pivot_roadmaps'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    analysis_id = db.Column(db.Integer, db.ForeignKey('skill_transfer_analyses.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    hours_per_week = db.Column(db.Integer, nullable=False)
    priority_balance = db.Column(db.JSON, nullable=True)
    milestones = db.Column(db.JSON, nullable=True)
    overall_progress_pct = db.Column(db.Float, default=0.0, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    user = db.relationship('User', backref=db.backref('pivot_roadmaps', lazy='dynamic'))
    target_role = db.relationship('Role', backref=db.backref('pivot_roadmaps', lazy='dynamic'))

    @property
    def estimated_total_tasks(self) -> int:
        if not self.milestones:
            return 0
        total = 0
        for item in self.milestones:
            tasks = item.get('tasks', []) if isinstance(item, dict) else []
            total += len(tasks)
        return total

    @property
    def start_date_or_today(self) -> date:
        return self.start_date or date.today()


class ProgressEntry(db.Model):
    __tablename__ = 'progress_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    roadmap_id = db.Column(db.Integer, db.ForeignKey('pivot_roadmaps.id'), nullable=False)
    entry_date = db.Column(db.Date, default=date.today, nullable=False)
    tasks_completed = db.Column(db.JSON, nullable=True)
    reflection = db.Column(db.Text, nullable=True)
    mood_rating = db.Column(db.Integer, nullable=True)
    obstacles_noted = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('progress_entries', lazy='dynamic'))
    roadmap = db.relationship('PivotRoadmap', backref=db.backref('progress_entries', lazy='dynamic'))
