from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, IntegerField, RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class CheckInForm(FlaskForm):
    mood_rating = RadioField(
        "How are you feeling about your pivot progress this week?",
        choices=[
            (1, '😞 Struggling'),
            (2, '😕 Difficult'),
            (3, '😐 Okay'),
            (4, '🙂 Good'),
            (5, '😊 Great')
        ],
        coerce=int,
        validators=[DataRequired()]
    )
    reflection = TextAreaField('Weekly reflection', validators=[Optional(), Length(max=2000)])
    obstacles_noted = TextAreaField('Any obstacles or blockers this week?', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Save Check-In')


class JourneySubmissionForm(FlaskForm):
    origin_role_id = SelectField('Your current/former role', coerce=int, validators=[DataRequired()])
    target_role_id = SelectField('The role you pivoted to (or are pivoting toward)', coerce=int, validators=[DataRequired()])
    origin_industry = StringField('Your original industry', validators=[DataRequired(), Length(max=100)])
    target_industry = StringField('Your target industry', validators=[DataRequired(), Length(max=100)])
    experience_at_pivot = IntegerField(
        'Years of experience in your original career when you started the pivot',
        validators=[DataRequired(), NumberRange(min=0, max=50)]
    )
    timeline_months = IntegerField(
        'How many months from decision to landing in your new role? (Or how many months so far if in progress)',
        validators=[DataRequired(), NumberRange(min=1, max=120)]
    )
    preparation_months = IntegerField(
        'How many months of active preparation (courses, networking, portfolio)?',
        validators=[DataRequired(), NumberRange(min=0, max=60)]
    )
    income_change_pct = FloatField(
        'Approximate income change at 12 months after pivoting (% — use negative for decrease, e.g. -20 for 20% decrease)',
        validators=[DataRequired(), NumberRange(min=-100, max=500)]
    )
    outcome_status = SelectField(
        'Current status of your pivot',
        choices=[
            ('completed', 'Completed — I am working in my new role'),
            ('in_progress', 'In Progress — I am still making the transition'),
            ('reversed', 'Reversed — I went back to my original field or a different direction')
        ],
        validators=[DataRequired()]
    )
    reversal_reason = TextAreaField(
        'If reversed: what led you to reverse the pivot? Be honest — this helps others.',
        validators=[Optional(), Length(max=2000)]
    )
    summary = TextAreaField(
        '3-sentence public summary of your journey (this is shown on the journey card)',
        validators=[DataRequired(), Length(min=50, max=600)]
    )
    what_worked = TextAreaField(
        'What worked? What approaches, resources, or decisions were most effective?',
        validators=[DataRequired(), Length(min=100, max=3000)]
    )
    what_failed = TextAreaField(
        "What failed or didn't work? What mistakes would you warn others about?",
        validators=[DataRequired(), Length(min=100, max=3000)]
    )
    unexpected_discoveries = TextAreaField(
        'What surprised you? What did you discover that you did not expect?',
        validators=[DataRequired(), Length(min=50, max=2000)]
    )
    advice_to_others = TextAreaField(
        'What is your single most important piece of advice to someone considering this same pivot?',
        validators=[DataRequired(), Length(min=50, max=1500)]
    )
    total_cost_inr = FloatField(
        'Approximate total financial cost of your transition in ₹ (courses, certifications, income gap, coaching, etc.) — optional',
        validators=[Optional(), NumberRange(min=0)]
    )
    geographic_region = SelectField(
        'Where are you located?',
        choices=[
            ('India - Bengaluru', 'India - Bengaluru'),
            ('India - Mumbai', 'India - Mumbai'),
            ('India - Delhi NCR', 'India - Delhi NCR'),
            ('India - Hyderabad', 'India - Hyderabad'),
            ('India - Pune', 'India - Pune'),
            ('India - Chennai', 'India - Chennai'),
            ('India - Remote', 'India - Remote / Work from Anywhere'),
            ('Southeast Asia', 'Southeast Asia'),
            ('Middle East', 'Middle East'),
            ('UK', 'United Kingdom'),
            ('USA', 'United States'),
            ('Canada', 'Canada'),
            ('Australia', 'Australia'),
            ('Other', 'Other')
        ],
        validators=[DataRequired()]
    )
    pseudonym = StringField(
        "Display name (optional — how should your story be attributed? e.g., 'Priya S.' or 'A. Kumar')",
        validators=[Optional(), Length(max=100)]
    )
    submitter_consented = BooleanField(
        'I consent to PathMap publishing my anonymized journey. I understand my name will not be displayed and I can request removal at any time by emailing privacy@pathmap.in.',
        validators=[DataRequired(message='You must consent to submission to share your journey.')]
    )
    submit = SubmitField('Submit My Journey')
