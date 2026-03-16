from datetime import datetime
from decimal import Decimal
from ..extensions import db


class SubscriptionPayment(db.Model):
    __tablename__ = 'subscription_payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    razorpay_payment_id = db.Column(db.String(200), nullable=False, unique=True)
    razorpay_subscription_id = db.Column(db.String(200), nullable=False)
    amount_inr = db.Column(db.Numeric(10, 2), nullable=False)
    plan_type = db.Column(db.String(50))
    payment_status = db.Column(db.String(50), default='captured')
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_number = db.Column(db.String(100), nullable=True)

    user = db.relationship('User', backref='subscription_payments')

    @property
    def amount_display(self) -> str:
        amount_val = Decimal(self.amount_inr or 0)
        return f"₹{amount_val:,.2f}"


class AdminAuditLog(db.Model):
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action_type = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(100))
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('User', backref='admin_actions')
