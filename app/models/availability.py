from .user import db

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # "09:00"
    end_time = db.Column(db.String(5), nullable=False)    # "10:00"
    is_booked = db.Column(db.Boolean, default=False)

    interviewer = db.relationship('User', backref='availability_slots')
