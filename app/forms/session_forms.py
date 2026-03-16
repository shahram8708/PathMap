from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, RadioField, SelectField, StringField, TextAreaField
from wtforms.fields import URLField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL


class BookingForm(FlaskForm):
    notes_from_booker = TextAreaField(
        "What would you like to discuss in this session? (Optional)",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'placeholder': (
                "e.g., I want to understand what a typical day looks like as a UX Designer, what skills are most valued, "
                "and whether my marketing background is an asset or liability in this transition."
            )
        }
    )


class SessionReviewForm(FlaskForm):
    rating = RadioField(
        'Overall rating',
        choices=[
            (1, '1 — Poor'),
            (2, '2 — Below average'),
            (3, '3 — Average'),
            (4, '4 — Good'),
            (5, '5 — Excellent')
        ],
        coerce=int,
        validators=[DataRequired()]
    )
    review_text = TextAreaField(
        'Your review',
        validators=[DataRequired(), Length(min=20, max=2000)],
        render_kw={
            'placeholder': (
                "Describe what the session covered, whether the provider gave you honest and useful insights, and how it "
                "helped (or didn't help) your career decision."
            )
        }
    )
    would_recommend = BooleanField('I would recommend this provider to others considering this career pivot')
    session_helped_decision = BooleanField('This session helped clarify my career decision')


class ProviderApplicationForm(FlaskForm):
    current_role_id = SelectField('Your current role', coerce=int, validators=[DataRequired()])
    proposed_display_name = StringField(
        'Your display name (first name + last initial or pseudonym)',
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={'placeholder': 'e.g., Rahul M. or DataCareer_Pro'}
    )
    proposed_bio = TextAreaField(
        'Your professional background',
        validators=[DataRequired(), Length(min=100, max=3000)],
        render_kw={'placeholder': 'Describe your career journey, expertise, and any career pivots you have made.'}
    )
    proposed_session_description = TextAreaField(
        'Describe exactly what happens in your session',
        validators=[DataRequired(), Length(min=80, max=2000)],
        render_kw={'placeholder': 'Explain the flow of your 45-60 minute shadow session and what attendees will learn.'}
    )
    session_format = StringField(
        'Session format',
        validators=[Optional(), Length(max=100)],
        render_kw={'placeholder': '45-minute video call via Google Meet / Zoom link provided after booking'}
    )
    proposed_price_inr = IntegerField(
        'Session price (₹)',
        validators=[DataRequired(), NumberRange(min=500, max=20000)],
        render_kw={'placeholder': 'e.g., 3500'}
    )
    why_good_provider = TextAreaField(
        'Why are you well-positioned to help career changers into your field?',
        validators=[DataRequired(), Length(min=50, max=1500)]
    )
    linkedin_url = URLField(
        'LinkedIn profile URL (optional)',
        validators=[Optional(), URL(), Length(max=500)]
    )
    industries_covered = StringField(
        'Industries you can speak to (comma-separated)',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': 'e.g., B2B SaaS, Fintech, Healthcare Tech'}
    )
    years_in_target_role = IntegerField(
        'Years in your current role',
        validators=[DataRequired(), NumberRange(min=1, max=40)]
    )
    consent = BooleanField(
        'I confirm that I will provide honest, non-promotional sessions. I understand that PathMap retains 12.5% of each booking as a platform fee.',
        validators=[DataRequired()]
    )


class ProviderEditForm(FlaskForm):
    current_role_id = SelectField('Your current role', coerce=int, validators=[DataRequired()])
    proposed_display_name = StringField(
        'Your display name',
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    proposed_bio = TextAreaField(
        'Your professional background',
        validators=[DataRequired(), Length(min=100, max=3000)]
    )
    proposed_session_description = TextAreaField(
        'Describe exactly what happens in your session',
        validators=[DataRequired(), Length(min=80, max=2000)]
    )
    session_format = StringField(
        'Session format',
        validators=[Optional(), Length(max=100)]
    )
    proposed_price_inr = IntegerField(
        'Session price (₹)',
        validators=[DataRequired(), NumberRange(min=500, max=20000)]
    )
    linkedin_url = URLField('LinkedIn profile URL (optional)', validators=[Optional(), URL(), Length(max=500)])
    industries_covered = StringField('Industries you can speak to', validators=[Optional(), Length(max=500)])
    years_in_target_role = IntegerField('Years in your current role', validators=[DataRequired(), NumberRange(min=1, max=40)])
    booking_url = URLField('Booking link (Calendly/Calendar)', validators=[Optional(), URL(), Length(max=500)])
    transition_story = TextAreaField('Career transition story', validators=[Optional(), Length(max=3000)])
    is_active = BooleanField('Currently accepting bookings')
