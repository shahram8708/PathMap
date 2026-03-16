from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import CheckConstraint

from ..extensions import db


class ShadowSessionProvider(db.Model):
    __tablename__ = 'shadow_session_providers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    current_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=False)
    transition_story = db.Column(db.Text, nullable=True)
    session_description = db.Column(db.Text, nullable=False)
    session_format = db.Column(db.String(100), nullable=True)
    price_inr = db.Column(db.Numeric(10, 2), nullable=False)
    booking_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    avg_rating = db.Column(db.Numeric(3, 2), default=0.0, nullable=False)
    total_sessions = db.Column(db.Integer, default=0, nullable=False)
    total_reviews = db.Column(db.Integer, default=0, nullable=False)
    industries_covered = db.Column(db.String(500), nullable=True)
    years_in_target_role = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('provider_profile', uselist=False))
    current_role = db.relationship('Role', backref=db.backref('session_providers', lazy='dynamic'))
    reviews = db.relationship('SessionReview', backref='provider', lazy='dynamic')
    bookings = db.relationship('SessionBooking', back_populates='provider', lazy='dynamic')

    def is_provider_for_user(self, user_id: int) -> bool:
        return self.user_id == user_id

    @property
    def price_display(self) -> str:
        return f"₹{float(self.price_inr):,.0f}" if self.price_inr is not None else "₹0"

    @property
    def rating_display(self) -> str:
        if self.total_reviews == 0 or not self.avg_rating:
            return "No reviews yet"
        return f"{float(self.avg_rating):.1f} ★"

    def __repr__(self):
        return f"<ShadowSessionProvider {self.display_name}>"


class SessionReview(db.Model):
    __tablename__ = 'session_reviews'
    __table_args__ = (
        db.UniqueConstraint('provider_id', 'reviewer_user_id', 'booking_id', name='uq_provider_reviewer_booking'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_session_review_rating_range')
    )

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('shadow_session_providers.id'), nullable=False, index=True)
    reviewer_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('session_bookings.id'), nullable=False, unique=True)
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=False)
    would_recommend = db.Column(db.Boolean, default=True, nullable=False)
    session_helped_decision = db.Column(db.Boolean, nullable=True)
    is_verified = db.Column(db.Boolean, default=True, nullable=False)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reviewer = db.relationship('User', backref=db.backref('session_reviews_given', lazy='dynamic'))

    def __repr__(self):
        return f"<SessionReview provider={self.provider_id} rating={self.rating}>"


class SessionBooking(db.Model):
    __tablename__ = 'session_bookings'

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('shadow_session_providers.id'), nullable=False, index=True)
    booker_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    amount_inr = db.Column(db.Numeric(10, 2), nullable=False)
    commission_inr = db.Column(db.Numeric(10, 2), nullable=False)
    provider_payout_inr = db.Column(db.Numeric(10, 2), nullable=False)
    razorpay_order_id = db.Column(db.String(200), nullable=True)
    razorpay_payment_id = db.Column(db.String(200), nullable=True)
    razorpay_signature = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False)
    payment_captured_at = db.Column(db.DateTime, nullable=True)
    session_scheduled_at = db.Column(db.DateTime, nullable=True)
    session_completed_at = db.Column(db.DateTime, nullable=True)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes_from_booker = db.Column(db.Text, nullable=True)
    session_link = db.Column(db.String(500), nullable=True)
    has_review = db.Column(db.Boolean, default=False, nullable=False)
    refund_reason = db.Column(db.Text, nullable=True)

    booker = db.relationship('User', foreign_keys=[booker_user_id], backref=db.backref('session_bookings_made', lazy='dynamic'))
    provider = db.relationship('ShadowSessionProvider', foreign_keys=[provider_id], back_populates='bookings')

    STATUS_LABELS = {
        'pending': 'Payment Pending',
        'paid': 'Paid',
        'session_scheduled': 'Session Scheduled',
        'session_completed': 'Session Completed',
        'refund_requested': 'Refund Requested',
        'refunded': 'Refunded',
        'disputed': 'Disputed'
    }

    @property
    def status_display(self) -> str:
        return self.STATUS_LABELS.get(self.status, 'Pending')

    @property
    def can_be_reviewed(self) -> bool:
        return self.status == 'session_completed' and not self.has_review

    @staticmethod
    def compute_commission(amount_inr: Decimal) -> tuple[Decimal, Decimal]:
        commission = (amount_inr * Decimal('0.125')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        payout = (amount_inr - commission).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return commission, payout

    def __repr__(self):
        return f"<SessionBooking {self.id} status={self.status}>"


class ProviderApplication(db.Model):
    __tablename__ = 'provider_applications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    application_status = db.Column(db.String(50), default='pending', nullable=False)
    proposed_display_name = db.Column(db.String(100), nullable=False)
    proposed_bio = db.Column(db.Text, nullable=False)
    proposed_session_description = db.Column(db.Text, nullable=False)
    proposed_price_inr = db.Column(db.Numeric(10, 2), nullable=False)
    why_good_provider = db.Column(db.Text, nullable=False)
    linkedin_url = db.Column(db.String(500), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_admin_id], post_update=True)

    def __repr__(self):
        return f"<ProviderApplication user={self.user_id} status={self.application_status}>"


class ResourceBookmark(db.Model):
    __tablename__ = 'resource_bookmarks'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'resource_id', name='uq_user_resource_bookmark'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('learning_resources.id'), nullable=False, index=True)
    bookmarked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    resource = db.relationship('LearningResource', backref=db.backref('bookmarks', lazy='dynamic'))

    def __repr__(self):
        return f"<ResourceBookmark user={self.user_id} resource={self.resource_id}>"


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text, nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_published = db.Column(db.Boolean, default=False, nullable=False)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    tags = db.Column(db.String(500), nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)

    author = db.relationship('User', backref=db.backref('blog_posts', lazy='dynamic'))

    def __repr__(self):
        return f"<BlogPost {self.slug}>"