import os
import json
from functools import wraps
from datetime import datetime, date, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app)
from flask_login import login_required, current_user
from flask_mail import Message

from app import db, mail
from app.models.user import User
from app.models.availability import Availability
from app.models.booking import Booking

main_bp = Blueprint('main', __name__)


# ── Role decorators ──────────────────────────────────────────────────────────

def interviewer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('interviewer', 'admin'):
            flash('Access denied.', 'error')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated


# ── Public pages ─────────────────────────────────────────────────────────────

@main_bp.route('/')
def home():
    return render_template('home.html')


@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')


# ── Client pages ─────────────────────────────────────────────────────────────

@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'interviewer':
        return redirect(url_for('main.interviewer_dashboard'))
    upcoming = (Booking.query
                .filter_by(client_id=current_user.id, status='confirmed')
                .join(Availability, Booking.availability_id == Availability.id)
                .filter(Availability.date >= date.today())
                .order_by(Availability.date, Availability.start_time)
                .limit(5).all())
    admin_data = None
    if current_user.is_admin:
        admin_data = {
            'total_users': User.query.count(),
            'total_clients': User.query.filter_by(role='client').count(),
            'total_interviewers': User.query.filter_by(role='interviewer').count(),
            'total_bookings': Booking.query.count(),
            'recent_bookings': (Booking.query
                                .order_by(Booking.created_at.desc())
                                .limit(8).all()),
        }
    return render_template('dashboard.html', upcoming=upcoming, admin_data=admin_data)


@main_bp.route('/schedule')
@login_required
def schedule():
    end_date = date.today() + timedelta(days=42)
    query = Availability.query.filter(
        Availability.date >= date.today(),
        Availability.date <= end_date
    )
    if current_user.role == 'interviewer':
        query = query.filter_by(interviewer_id=current_user.id)
    slots = query.order_by(Availability.date, Availability.start_time).all()

    slots_data = []
    for s in slots:
        d = {
            'id': s.id,
            'date': s.date.isoformat(),
            'start': s.start_time,
            'end': s.end_time,
            'interviewer': s.interviewer.username,
            'interviewer_id': s.interviewer_id,
            'booked': s.is_booked,
            'booked_by': '',
            'session_type': '',
        }
        if s.is_booked and s.booking:
            d['booked_by'] = s.booking.client.username if s.booking.client else ''
            d['session_type'] = s.booking.session_type or 'mock_interview'
        slots_data.append(d)

    user_credits = {
        'session': current_user.session_credits,
        'mentoring': current_user.mentoring_credits,
    }
    return render_template('schedule.html',
        slots_json=json.dumps(slots_data),
        user_credits_json=json.dumps(user_credits),
        today=date.today().isoformat()
    )


@main_bp.route('/schedule/book/<int:availability_id>', methods=['POST'])
@login_required
def book_slot(availability_id):
    if current_user.role == 'interviewer':
        flash('Interviewers cannot book sessions.', 'error')
        return redirect(url_for('main.schedule'))

    session_type = request.form.get('session_type', 'mock_interview')
    slot = Availability.query.get_or_404(availability_id)

    if slot.is_booked:
        flash('That slot was just booked by someone else.', 'error')
        return redirect(url_for('main.schedule'))

    # Credit checks per session type
    if session_type == 'mock_interview':
        if current_user.session_credits < 1:
            flash('No session credits — purchase a package to book mock interviews.', 'error')
            return redirect(url_for('main.pricing'))
    elif session_type == 'mentoring':
        if current_user.mentoring_credits < 1:
            flash('No mentoring credits — upgrade your package to access career mentoring.', 'error')
            return redirect(url_for('main.pricing'))
    # resume_review and linkedin_review are free

    type_labels = {
        'mock_interview': 'Mock Interview',
        'resume_review': 'Resume Review',
        'linkedin_review': 'LinkedIn Review',
        'mentoring': 'Career Mentoring',
    }

    try:
        slot.is_booked = True
        if session_type == 'mock_interview':
            current_user.session_credits -= 1
        elif session_type == 'mentoring':
            current_user.mentoring_credits -= 1
        booking = Booking(
            client_id=current_user.id,
            interviewer_id=slot.interviewer_id,
            availability_id=slot.id,
            session_type=session_type
        )
        db.session.add(booking)
        db.session.commit()
        label = type_labels.get(session_type, session_type)
        flash(f'{label} booked for {slot.date.strftime("%B %d")} at {slot.start_time}!', 'success')
    except Exception:
        db.session.rollback()
        flash('Something went wrong. Please try again.', 'error')

    return redirect(url_for('main.dashboard'))


@main_bp.route('/resume-review', methods=['GET', 'POST'])
@login_required
def resume_review():
    if request.method == 'POST':
        file = request.files.get('resume')
        if not file or file.filename == '':
            flash('Please select a file to upload.', 'error')
            return redirect(url_for('main.resume_review'))

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ('.pdf', '.doc', '.docx'):
            flash('Only PDF, DOC, or DOCX files are accepted.', 'error')
            return redirect(url_for('main.resume_review'))

        filename = file.filename
        file_data = file.read()

        try:
            msg = Message(
                subject=f'Resume Review — {current_user.username}',
                recipients=['scholarviewsinc@gmail.com'],
                body=(
                    f'Resume submitted by {current_user.username} ({current_user.email})\n'
                    f'Submitted: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}'
                )
            )
            msg.attach(filename, file.content_type or 'application/octet-stream', file_data)
            mail.send(msg)
            flash('Your resume was submitted successfully! Expect feedback within 48 hours.', 'success')
        except Exception:
            flash('Resume received but email delivery failed — please contact us directly.', 'warning')

        return redirect(url_for('main.resume_review'))

    return render_template('resume_review.html')


@main_bp.route('/linkedin-review', methods=['GET', 'POST'])
@login_required
def linkedin_review():
    if request.method == 'POST':
        linkedin_url = request.form.get('linkedin_url', '').strip()
        notes = request.form.get('notes', '').strip()
        if not linkedin_url:
            flash('Please provide your LinkedIn profile URL.', 'error')
            return redirect(url_for('main.linkedin_review'))
        try:
            msg = Message(
                subject=f'LinkedIn Review — {current_user.username}',
                recipients=['scholarviewsinc@gmail.com'],
                body=(
                    f'LinkedIn review requested by {current_user.username} ({current_user.email})\n'
                    f'Profile: {linkedin_url}\n'
                    f'Notes: {notes or "None"}\n'
                    f'Submitted: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}'
                )
            )
            mail.send(msg)
            flash('LinkedIn profile submitted! Expect feedback within 48 hours.', 'success')
        except Exception:
            flash('Request received but email delivery failed — contact us directly.', 'warning')
        return redirect(url_for('main.linkedin_review'))
    return render_template('linkedin_review.html')


@main_bp.route('/grad-studies')
@login_required
def grad_studies():
    return render_template('grad_studies.html')


@main_bp.route('/resources')
def resources():
    return render_template('resources.html')


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/interviewers')
def our_interviewers():
    return render_template('interviewers.html')


@main_bp.route('/faq')
def faq():
    return render_template('faq.html')


# ── Interviewer pages ─────────────────────────────────────────────────────────

@main_bp.route('/interviewer/dashboard')
@login_required
@interviewer_required
def interviewer_dashboard():
    upcoming = (Booking.query
                .filter_by(interviewer_id=current_user.id, status='confirmed')
                .join(Availability, Booking.availability_id == Availability.id)
                .filter(Availability.date >= date.today())
                .order_by(Availability.date, Availability.start_time)
                .all())
    return render_template('interviewer/dashboard.html', upcoming=upcoming)


@main_bp.route('/interviewer/availability')
@login_required
@interviewer_required
def interviewer_availability():
    slots = (Availability.query
             .filter_by(interviewer_id=current_user.id)
             .order_by(Availability.date, Availability.start_time)
             .all())
    return render_template('interviewer/availability.html', slots=slots)


@main_bp.route('/interviewer/availability/add', methods=['POST'])
@login_required
@interviewer_required
def add_availability():
    date_str = request.form.get('date', '')
    start = request.form.get('start_time', '')
    end = request.form.get('end_time', '')

    if not date_str or not start or not end:
        flash('All fields are required.', 'error')
        return redirect(url_for('main.interviewer_availability'))

    try:
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if slot_date < date.today():
            flash('Cannot add slots in the past.', 'error')
            return redirect(url_for('main.interviewer_availability'))
        if start >= end:
            flash('End time must be after start time.', 'error')
            return redirect(url_for('main.interviewer_availability'))

        slot = Availability(
            interviewer_id=current_user.id,
            date=slot_date,
            start_time=start,
            end_time=end
        )
        db.session.add(slot)
        db.session.commit()
        flash('Availability slot added.', 'success')
    except ValueError:
        flash('Invalid date format.', 'error')
    except Exception:
        db.session.rollback()
        flash('Something went wrong. Please try again.', 'error')

    return redirect(url_for('main.interviewer_availability'))


@main_bp.route('/interviewer/availability/delete/<int:slot_id>', methods=['POST'])
@login_required
@interviewer_required
def delete_availability(slot_id):
    slot = Availability.query.get_or_404(slot_id)
    if slot.interviewer_id != current_user.id:
        flash('Not authorized.', 'error')
        return redirect(url_for('main.interviewer_availability'))
    if slot.is_booked:
        flash('Cannot delete a slot that is already booked.', 'error')
        return redirect(url_for('main.interviewer_availability'))
    try:
        db.session.delete(slot)
        db.session.commit()
        flash('Slot removed.', 'success')
    except Exception:
        db.session.rollback()
        flash('Something went wrong.', 'error')
    return redirect(url_for('main.interviewer_availability'))
