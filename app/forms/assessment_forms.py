from flask_wtf import FlaskForm
from wtforms import RadioField, IntegerField, SelectField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length


class WorkValuesForm(FlaskForm):
    choices = [
        (1, 'Not Important'),
        (2, 'Slightly Important'),
        (3, 'Moderately Important'),
        (4, 'Very Important'),
        (5, 'Essential')
    ]
    autonomy = RadioField('Autonomy', choices=choices, coerce=int, validators=[DataRequired()])
    creativity = RadioField('Creativity', choices=choices, coerce=int, validators=[DataRequired()])
    stability = RadioField('Stability', choices=choices, coerce=int, validators=[DataRequired()])
    income = RadioField('Financial Reward', choices=choices, coerce=int, validators=[DataRequired()])
    impact = RadioField('Impact', choices=choices, coerce=int, validators=[DataRequired()])
    collaboration = RadioField('Collaboration', choices=choices, coerce=int, validators=[DataRequired()])
    learning = RadioField('Continuous Learning', choices=choices, coerce=int, validators=[DataRequired()])
    prestige = RadioField('Prestige & Recognition', choices=choices, coerce=int, validators=[DataRequired()])
    flexibility = RadioField('Flexibility', choices=choices, coerce=int, validators=[DataRequired()])
    social = RadioField('Social Connection', choices=choices, coerce=int, validators=[DataRequired()])


class WorkStyleForm(FlaskForm):
    q1 = IntegerField('q1', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q2 = IntegerField('q2', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q3 = IntegerField('q3', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q4 = IntegerField('q4', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q5 = IntegerField('q5', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q6 = IntegerField('q6', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q7 = IntegerField('q7', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q8 = IntegerField('q8', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q9 = IntegerField('q9', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q10 = IntegerField('q10', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q11 = IntegerField('q11', validators=[DataRequired(), NumberRange(min=1, max=7)])
    q12 = IntegerField('q12', validators=[DataRequired(), NumberRange(min=1, max=7)])


class SkillsForm(FlaskForm):
    written_communication = IntegerField('Written Communication', validators=[DataRequired(), NumberRange(min=0, max=4)])
    verbal_presentation = IntegerField('Verbal Presentation', validators=[DataRequired(), NumberRange(min=0, max=4)])
    stakeholder_management = IntegerField('Stakeholder Management', validators=[DataRequired(), NumberRange(min=0, max=4)])
    negotiation = IntegerField('Negotiation', validators=[DataRequired(), NumberRange(min=0, max=4)])
    active_listening = IntegerField('Active Listening', validators=[DataRequired(), NumberRange(min=0, max=4)])
    data_analysis = IntegerField('Data Analysis', validators=[DataRequired(), NumberRange(min=0, max=4)])
    critical_thinking = IntegerField('Critical Thinking', validators=[DataRequired(), NumberRange(min=0, max=4)])
    problem_solving = IntegerField('Problem Solving', validators=[DataRequired(), NumberRange(min=0, max=4)])
    financial_modeling = IntegerField('Financial Modeling', validators=[DataRequired(), NumberRange(min=0, max=4)])
    research_and_synthesis = IntegerField('Research & Synthesis', validators=[DataRequired(), NumberRange(min=0, max=4)])
    python_programming = IntegerField('Python Programming', validators=[DataRequired(), NumberRange(min=0, max=4)])
    sql_and_databases = IntegerField('SQL & Databases', validators=[DataRequired(), NumberRange(min=0, max=4)])
    excel_and_spreadsheets = IntegerField('Excel & Spreadsheets', validators=[DataRequired(), NumberRange(min=0, max=4)])
    data_visualization = IntegerField('Data Visualization', validators=[DataRequired(), NumberRange(min=0, max=4)])
    digital_tools_and_saas = IntegerField('Digital Tools & SaaS', validators=[DataRequired(), NumberRange(min=0, max=4)])
    design_thinking = IntegerField('Design Thinking', validators=[DataRequired(), NumberRange(min=0, max=4)])
    content_creation = IntegerField('Content Creation', validators=[DataRequired(), NumberRange(min=0, max=4)])
    visual_communication = IntegerField('Visual Communication', validators=[DataRequired(), NumberRange(min=0, max=4)])
    storytelling = IntegerField('Storytelling', validators=[DataRequired(), NumberRange(min=0, max=4)])
    ideation_and_brainstorming = IntegerField('Ideation & Brainstorming', validators=[DataRequired(), NumberRange(min=0, max=4)])
    team_management = IntegerField('Team Management', validators=[DataRequired(), NumberRange(min=0, max=4)])
    project_management = IntegerField('Project Management', validators=[DataRequired(), NumberRange(min=0, max=4)])
    strategic_planning = IntegerField('Strategic Planning', validators=[DataRequired(), NumberRange(min=0, max=4)])
    mentoring_and_coaching = IntegerField('Mentoring & Coaching', validators=[DataRequired(), NumberRange(min=0, max=4)])
    decision_making_under_pressure = IntegerField('Decision Making Under Pressure', validators=[DataRequired(), NumberRange(min=0, max=4)])
    marketing_and_growth = IntegerField('Marketing & Growth', validators=[DataRequired(), NumberRange(min=0, max=4)])
    finance_and_accounting = IntegerField('Finance & Accounting', validators=[DataRequired(), NumberRange(min=0, max=4)])
    product_development = IntegerField('Product Development', validators=[DataRequired(), NumberRange(min=0, max=4)])
    operations_and_process = IntegerField('Operations & Process', validators=[DataRequired(), NumberRange(min=0, max=4)])
    customer_research = IntegerField('Customer Research', validators=[DataRequired(), NumberRange(min=0, max=4)])


class ConstraintsForm(FlaskForm):
    income_floor = IntegerField(
        'Minimum monthly income (₹)',
        validators=[DataRequired(), NumberRange(min=0, max=10_000_000)]
    )
    hours_per_week = IntegerField(
        'Hours per week',
        validators=[DataRequired(), NumberRange(min=1, max=40)]
    )
    timeline_months = SelectField(
        'Timeline',
        choices=[(3, '3 months'), (6, '6 months'), (9, '9 months'), (12, '12 months'), (18, '18 months'), (24, '24+ months')],
        coerce=int,
        validators=[DataRequired()]
    )
    geographic_flexibility = RadioField(
        'Geographic flexibility',
        choices=[
            ('local', 'Local only — must stay in my city'),
            ('national', 'National — open to other Indian cities'),
            ('global', 'Global — open to international roles'),
            ('remote_only', 'Remote only — fully distributed work')
        ],
        validators=[DataRequired()]
    )


class VisionForm(FlaskForm):
    vision_day = TextAreaField(
        'Ideal workday',
        validators=[DataRequired(), Length(min=30, max=1500)]
    )
    vision_impact = TextAreaField(
        'Desired impact',
        validators=[DataRequired(), Length(min=30, max=1500)]
    )
    vision_regret = TextAreaField(
        'Regret prevention',
        validators=[DataRequired(), Length(min=30, max=1500)]
    )
