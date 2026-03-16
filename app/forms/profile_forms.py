from wtforms import StringField, SelectField, IntegerField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, EqualTo, ValidationError, URL
from flask_wtf import FlaskForm


class UpdateProfileForm(FlaskForm):
    first_name = StringField('First name', validators=[DataRequired(), Length(min=1, max=100)])
    current_role_id = SelectField('Current role', coerce=int, validators=[Optional()])
    years_experience = IntegerField('Years of experience', validators=[Optional(), NumberRange(min=0, max=50)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current password', validators=[DataRequired()])
    new_password = PasswordField('New password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_new_password = PasswordField('Confirm new password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])


class NotificationPreferencesForm(FlaskForm):
    email_weekly_checkin = BooleanField('Weekly progress check-in reminders')
    email_journey_published = BooleanField('Notification when my journey submission is published')
    email_session_updates = BooleanField('Session booking updates and confirmations')
    email_product_updates = BooleanField('PathMap product updates and new features')
    email_marketing = BooleanField('Career tips and inspiration emails')


class GDPRDeletionForm(FlaskForm):
    confirmation_text = StringField('Type DELETE to confirm', validators=[DataRequired()])

    def validate_confirmation_text(self, field):
        if field.data != 'DELETE':
            raise ValidationError('Please type DELETE exactly to confirm permanent deletion.')


class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=300)])
    slug = StringField('Slug', validators=[Optional(), Length(max=300)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=100)])
    excerpt = TextAreaField('Excerpt', validators=[Optional(), Length(max=500)])
    tags = StringField('Tags', validators=[Optional(), Length(max=500)])
    is_published = BooleanField('Publish immediately')
    cover_image_url = StringField('Cover image URL', validators=[Optional(), URL(), Length(max=500)])


class JourneyModerationForm(FlaskForm):
    rejection_reason = TextAreaField('Rejection reason', validators=[Optional(), Length(max=1000)])


class ProviderRejectionForm(FlaskForm):
    rejection_reason = TextAreaField('Rejection reason', validators=[DataRequired(), Length(min=20, max=1000)])


class SimpleActionForm(FlaskForm):
    """CSRF-protected action form with no fields."""
    pass
