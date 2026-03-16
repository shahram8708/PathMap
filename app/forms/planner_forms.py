from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class RoadmapGenerationForm(FlaskForm):
    analysis_id = SelectField('Analysis', coerce=int, validators=[DataRequired()])
    hours_per_week = IntegerField('Hours per week', validators=[DataRequired(), NumberRange(min=1, max=80)])
    priority_skills = IntegerField('Skill priority (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    priority_network = IntegerField('Network priority (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    priority_portfolio = IntegerField('Portfolio priority (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    start_date = DateField('Start date', validators=[Optional()])
    submit = SubmitField('Generate roadmap')


class DecisionStepForm(FlaskForm):
    submit = SubmitField('Save step')
