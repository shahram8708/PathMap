from datetime import datetime
from ..extensions import db


class UserAssessment(db.Model):
    __tablename__ = 'user_assessments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    values_data = db.Column(db.JSON, nullable=True)
    values_completed = db.Column(db.Boolean, default=False, nullable=False)
    workstyle_data = db.Column(db.JSON, nullable=True)
    workstyle_completed = db.Column(db.Boolean, default=False, nullable=False)
    skills_data = db.Column(db.JSON, nullable=True)
    skills_completed = db.Column(db.Boolean, default=False, nullable=False)
    constraints_data = db.Column(db.JSON, nullable=True)
    constraints_completed = db.Column(db.Boolean, default=False, nullable=False)
    vision_data = db.Column(db.JSON, nullable=True)
    vision_completed = db.Column(db.Boolean, default=False, nullable=False)
    profile_summary = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('assessments', lazy='dynamic'))

    @property
    def completed_modules_count(self) -> int:
        return sum([
            bool(self.values_completed),
            bool(self.workstyle_completed),
            bool(self.skills_completed),
            bool(self.constraints_completed),
            bool(self.vision_completed)
        ])

    @property
    def is_fully_complete(self) -> bool:
        return self.completed_modules_count == 5

    @property
    def completion_percentage(self) -> float:
        return (self.completed_modules_count / 5) * 100 if self.completed_modules_count else 0.0
