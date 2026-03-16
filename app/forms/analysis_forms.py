from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField
from wtforms.validators import DataRequired
from ..models.role import Role


class NewAnalysisForm(FlaskForm):
    origin_role_id = HiddenField('Origin Role ID', validators=[DataRequired()])
    target_role_ids = HiddenField('Target Role IDs', validators=[DataRequired()])
    submit = SubmitField('Analyze These Paths')

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators)
        if not valid:
            return False

        try:
            origin_id = int(self.origin_role_id.data)
        except Exception:
            self.origin_role_id.errors.append('Select your current role.')
            return False

        raw_targets = [item.strip() for item in (self.target_role_ids.data or '').split(',') if item.strip()]
        try:
            target_ids = [int(x) for x in raw_targets]
        except Exception:
            self.target_role_ids.errors.append('Select at least one valid target role.')
            return False

        if not target_ids:
            self.target_role_ids.errors.append('Select at least one target role.')
            return False
        if len(target_ids) > 3:
            self.target_role_ids.errors.append('You can analyze up to 3 target roles at once.')
            return False
        if origin_id in target_ids:
            self.target_role_ids.errors.append('Origin and target roles must be different.')
            return False

        origin_exists = Role.query.filter_by(id=origin_id, is_active=True).first()
        if not origin_exists:
            self.origin_role_id.errors.append('Select a valid current role.')
            return False

        active_targets = Role.query.filter(Role.id.in_(target_ids), Role.is_active.is_(True)).all()
        if len(active_targets) != len(set(target_ids)):
            self.target_role_ids.errors.append('One or more selected target roles are invalid or inactive.')
            return False

        self.cleaned_origin_id = origin_id
        self.cleaned_target_ids = target_ids
        return True
