from .user import db
from datetime import datetime

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    availability_id = db.Column(db.Integer, db.ForeignKey('availability.id'), nullable=False)
    status = db.Column(db.String(20), default='confirmed')  # confirmed, cancelled, completed
    session_type = db.Column(db.String(50), default='mock_interview')  # mock_interview, resume_review, linkedin_review, mentoring
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('User', foreign_keys=[client_id], backref='bookings_as_client')
    interviewer = db.relationship('User', foreign_keys=[interviewer_id], backref='bookings_as_interviewer')
    slot = db.relationship('Availability', backref='booking')
