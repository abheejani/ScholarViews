import re
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app)
from flask_login import login_user, login_required, logout_user
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from app import db, mail
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

# ── Token helpers ─────────────────────────────────────────────────────────────

def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def _generate_token(email, salt):
    return _serializer().dumps(email, salt=salt)

def _verify_token(token, salt, max_age=3600):
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None

# ── Mail helpers ──────────────────────────────────────────────────────────────

def _send_verification_email(user):
    token = _generate_token(user.email, salt='email-verify')
    user.verification_token = token
    db.session.commit()
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    try:
        msg = Message(
            subject='Verify your ScholarViews email',
            recipients=[user.email],
            body=(
                f'Hi {user.username},\n\n'
                f'Click the link below to verify your email address. '
                f'This link expires in 1 hour.\n\n'
                f'{verify_url}\n\n'
                f'If you did not create an account, ignore this email.\n\n'
                f'— The ScholarViews Team'
            )
        )
        mail.send(msg)
    except Exception:
        pass  # email delivery failure is non-fatal on signup


def _send_reset_email(user):
    token = _generate_token(user.email, salt='password-reset')
    user.reset_token = token
    user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.commit()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    try:
        msg = Message(
            subject='Reset your ScholarViews password',
            recipients=[user.email],
            body=(
                f'Hi {user.username},\n\n'
                f'Click the link below to reset your password. '
                f'This link expires in 1 hour.\n\n'
                f'{reset_url}\n\n'
                f'If you did not request a password reset, ignore this email.\n\n'
                f'— The ScholarViews Team'
            )
        )
        mail.send(msg)
    except Exception:
        pass


# ── Password validation ───────────────────────────────────────────────────────

def validate_password(password):
    errors = []
    if len(password) < 8:
        errors.append('at least 8 characters')
    if not any(c.isdigit() for c in password):
        errors.append('at least one number')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append('at least one special character')
    return errors


# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'error')
            return redirect(url_for('auth.signup'))

        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('auth.signup'))

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.signup'))

        errors = validate_password(password)
        if errors:
            flash(f'Password needs: {", ".join(errors)}.', 'error')
            return redirect(url_for('auth.signup'))

        try:
            user = User(username=username, email=email, is_verified=False)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            _send_verification_email(user)
            flash('Account created! Check your email to verify your address.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return redirect(url_for('auth.signup'))

    return render_template('login_page/signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            if user.role == 'interviewer':
                return redirect(url_for('main.interviewer_dashboard'))
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login_page/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    email = _verify_token(token, salt='email-verify', max_age=3600)
    if email is None:
        flash('Verification link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if user is None:
        flash('Account not found.', 'error')
        return redirect(url_for('auth.login'))

    if user.is_verified:
        flash('Email already verified. You can log in.', 'info')
        return redirect(url_for('auth.login'))

    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    flash('Email verified! You can now book sessions.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    from flask_login import current_user
    if current_user.is_verified:
        flash('Your email is already verified.', 'info')
        return redirect(url_for('main.dashboard'))
    _send_verification_email(current_user)
    flash('Verification email resent. Check your inbox.', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show the same message to avoid email enumeration
        if user:
            _send_reset_email(user)
        flash('If that email is in our system, a reset link has been sent.', 'info')
        return redirect(url_for('auth.forgot_password'))
    return render_template('login_page/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = _verify_token(token, salt='password-reset', max_age=3600)
    if email is None:
        flash('Reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))

    user = User.query.filter_by(email=email).first()
    if user is None or user.reset_token != token:
        flash('Reset link is invalid or has already been used.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        errors = validate_password(password)
        if errors:
            flash(f'Password needs: {", ".join(errors)}.', 'error')
            return redirect(url_for('auth.reset_password', token=token))

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash('Password updated. You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('login_page/reset_password.html', token=token)
