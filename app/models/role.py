from datetime import datetime
from ..extensions import db


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    sub_category = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    skill_requirements = db.relationship('RoleSkillRequirement', back_populates='role', cascade='all, delete-orphan')
    learning_resources = db.relationship(
        'LearningResource',
        secondary='role_skill_requirements',
        primaryjoin='Role.id==RoleSkillRequirement.role_id',
        secondaryjoin='LearningResource.skill_id==RoleSkillRequirement.skill_id',
        viewonly=True,
        lazy='dynamic'
    )

    def __repr__(self):
        return f"<Role {self.title}>"


class Skill(db.Model):
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    role_requirements = db.relationship('RoleSkillRequirement', back_populates='skill', cascade='all, delete-orphan')
    learning_resources = db.relationship('LearningResource', back_populates='skill', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Skill {self.name}>"


class RoleSkillRequirement(db.Model):
    __tablename__ = 'role_skill_requirements'
    __table_args__ = (db.UniqueConstraint('role_id', 'skill_id', name='uq_role_skill_requirement'),)

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False, index=True)
    importance_weight = db.Column(db.Float, nullable=False)
    transfer_type = db.Column(db.String(50), nullable=False)

    role = db.relationship('Role', back_populates='skill_requirements')
    skill = db.relationship('Skill', back_populates='role_requirements')

    def __repr__(self):
        return f"<RoleSkillRequirement role={self.role_id} skill={self.skill_id}>"


class LearningResource(db.Model):
    __tablename__ = 'learning_resources'

    id = db.Column(db.Integer, primary_key=True)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    provider = db.Column(db.String(200), nullable=False)
    format = db.Column(db.String(100), nullable=True)
    cost_tier = db.Column(db.String(50), nullable=True)
    estimated_hours = db.Column(db.Float, nullable=False)
    url = db.Column(db.String(500), nullable=False)
    quality_rating = db.Column(db.Float, default=4.0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    skill = db.relationship('Skill', back_populates='learning_resources')

    def __repr__(self):
        return f"<LearningResource {self.title[:30]}>"
