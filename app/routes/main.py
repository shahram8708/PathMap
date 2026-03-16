from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    flash,
    redirect,
    url_for,
    abort
)
from flask_mail import Message

from ..extensions import mail
from ..forms.auth_forms import ContactForm
from ..models.journey import Journey
from ..models.session import BlogPost


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    journey_previews = Journey.query.filter_by(is_published=True).limit(2).all()
    featured_roles = [
        'Software Engineer',
        'Data Scientist',
        'UX Designer',
        'Product Manager',
        'Financial Analyst',
        'Marketing Manager'
    ]
    return render_template(
        'main/index.html',
        journey_previews=journey_previews,
        featured_roles=featured_roles
    )


@main_bp.route('/about')
def about():
    return render_template('main/about.html')


@main_bp.route('/how-it-works')
def how_it_works():
    return render_template('main/how_it_works.html')


@main_bp.route('/pricing')
def pricing():
    monthly_amount_paise = current_app.config.get('RAZORPAY_MONTHLY_PRICE_PAISE', 149900)
    annual_amount_paise = current_app.config.get('RAZORPAY_ANNUAL_PRICE_PAISE', 1199900)
    razorpay_key_id = current_app.config.get('RAZORPAY_KEY_ID', '')
    return render_template(
        'main/pricing.html',
        monthly_amount_paise=monthly_amount_paise,
        annual_amount_paise=annual_amount_paise,
        razorpay_key_id=razorpay_key_id
    )


@main_bp.route('/blog')
def blog_index():
    page = request.args.get('page', 1, type=int)
    pagination = (
        BlogPost.query
        .filter_by(is_published=True)
        .order_by(BlogPost.published_at.desc())
        .paginate(page=page, per_page=9, error_out=False)
    )
    posts = pagination.items
    return render_template('main/blog.html', posts=posts, pagination=pagination)


@main_bp.route('/blog/<string:slug>')
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first()
    if not post or not post.is_published:
        abort(404)

    reading_time = max(1, len(post.content.split()) // 200)
    related_posts = (
        BlogPost.query
        .filter(BlogPost.is_published.is_(True), BlogPost.id != post.id)
        .order_by(BlogPost.published_at.desc())
        .limit(2)
        .all()
    )

    return render_template(
        'main/blog_post.html',
        post=post,
        reading_time=reading_time,
        related_posts=related_posts
    )


@main_bp.route('/contact', methods=['GET'])
def contact():
    form = ContactForm()
    return render_template('main/contact.html', form=form)


@main_bp.route('/contact', methods=['POST'])
def contact_submit():
    form = ContactForm()
    if form.validate_on_submit():
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        recipients = [sender] if sender else []
        msg = Message(
            subject=f"[PathMap Contact] {form.subject.data}",
            sender=sender,
            recipients=recipients
        )
        msg.body = (
            f"Name: {form.name.data}\n"
            f"Email: {form.email.data}\n\n"
            f"Message:\n{form.message.data}"
        )

        try:
            if recipients:
                mail.send(msg)
            flash('Thanks for reaching out — we will respond within one business day.', 'success')
        except Exception:
            flash('We could not send your message right now. Please try again.', 'danger')
        return redirect(url_for('main.contact'))

    flash('Please correct the highlighted errors and try again.', 'danger')
    return render_template('main/contact.html', form=form)


@main_bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html')


@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html')


@main_bp.route('/features')
def features():
    return render_template('main/features.html')


@main_bp.route('/for-teams')
def for_teams():
    return render_template('main/for_teams.html', title='PathMap for Teams')
