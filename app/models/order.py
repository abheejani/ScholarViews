from .user import db
from datetime import datetime

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stripe_session_id = db.Column(db.String(200), unique=True, nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    session_credits_granted = db.Column(db.Integer, nullable=False, default=0)
    mentoring_credits_granted = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='orders')
