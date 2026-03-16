from datetime import datetime
from ..extensions import db


class SkillTransferAnalysis(db.Model):
    __tablename__ = 'skill_transfer_analyses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    origin_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    target_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_skill_overrides = db.Column(db.JSON, nullable=True)
    transfer_score = db.Column(db.Float, nullable=True)
    gap_score = db.Column(db.Float, nullable=True)
    direct_skills = db.Column(db.JSON, nullable=True)
    partial_skills = db.Column(db.JSON, nullable=True)
    gap_skills = db.Column(db.JSON, nullable=True)
    estimated_learning_hours = db.Column(db.Float, nullable=True)
    feasibility_score = db.Column(db.Float, nullable=True)
    feasibility_breakdown = db.Column(db.JSON, nullable=True)
    feasibility_narrative = db.Column(db.Text, nullable=True)
    is_saved = db.Column(db.Boolean, default=True, nullable=False)
    decision_data = db.Column(db.JSON, nullable=True)
    decision_completed = db.Column(db.Boolean, default=False, nullable=False)
    decision_summary_text = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('skill_transfer_analyses', lazy='dynamic'))
    origin_role = db.relationship('Role', foreign_keys=[origin_role_id])
    target_role = db.relationship('Role', foreign_keys=[target_role_id])

    @property
    def decision_summary(self):
        return self.decision_data or {}

    @decision_summary.setter
    def decision_summary(self, value):
        self.decision_data = value

    def __repr__(self):
        return f"<SkillTransferAnalysis {self.id} origin={self.origin_role_id} target={self.target_role_id}>"
