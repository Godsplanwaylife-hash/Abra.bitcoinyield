from urllib.parse import urlparse

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, URLSafeTimedSerializer

from emailer import APP_NAME, send_templated
from forms import ForgotForm, LoginForm, ResetForm, SignupForm, VerifyForm
from models import CODE_MINUTES, User, db

bp = Blueprint("auth", __name__)

RESET_MAX_AGE = 3600  # reset links last 1 hour


def _safe_next(target):
    """Only allow same-site relative redirects."""
    if target and not urlparse(target).netloc and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("market.home")


# ---------- helpers ----------
def _send_verification(user):
    code = user.set_verify_code()
    db.session.commit()
    send_templated(
        user.email, f"Your {APP_NAME} verification code",
        "Verify your email",
        [f"Hi {user.username},", "Enter this code to finish creating your account:"],
        code=code,
        footer=f"The code expires in {CODE_MINUTES} minutes. If you didn't create an account, you can ignore this email.",
    )


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def _make_reset_token(user):
    # The last chars of the password hash change when the password changes,
    # which makes each reset link single-use.
    return _serializer().dumps({"uid": user.id, "fp": user.password_hash[-12:]})


def _user_from_reset_token(token):
    try:
        data = _serializer().loads(token, max_age=RESET_MAX_AGE)
    except BadSignature:  # also covers expired tokens
        return None
    user = db.session.get(User, data.get("uid"))
    if user and user.password_hash[-12:] == data.get("fp"):
        return user
    return None


def _pending_user():
    uid = session.get("pending_uid")
    return db.session.get(User, uid) if uid else None


# ---------- signup / verify ----------
@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("market.home"))
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip().lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session["pending_uid"] = user.id
        _send_verification(user)
        flash("We sent a 6-digit code to your email. Enter it to finish signing up.", "success")
        return redirect(url_for("auth.verify"))
    return render_template("signup.html", form=form)


@bp.route("/verify", methods=["GET", "POST"])
def verify():
    user = _pending_user()
    if not user or user.email_verified:
        return redirect(url_for("auth.login"))
    form = VerifyForm()
    if form.validate_on_submit():
        ok = user.check_verify_code(form.code.data.strip())
        if ok:
            user.email_verified = True
            user.verify_code_hash = None
            user.verify_expires = None
            db.session.commit()
            session.pop("pending_uid", None)
            login_user(user)
            send_templated(user.email, f"Welcome to {APP_NAME}", "Welcome!",
                           [f"Hi {user.username},", "Your email is verified and your account is ready to use."])
            flash("Email verified. Welcome!", "success")
            return redirect(url_for("market.home"))
        db.session.commit()  # saves the attempt counter
        flash("That code is wrong or expired. You can request a new one below.", "error")
    return render_template("verify.html", form=form, email=user.email)


@bp.route("/verify/resend", methods=["POST"])
def resend_code():
    user = _pending_user()
    if not user or user.email_verified:
        return redirect(url_for("auth.login"))
    if user.code_sent_seconds_ago() < 60:
        flash("Please wait a minute before requesting another code.", "error")
    else:
        _send_verification(user)
        flash("A new code has been sent.", "success")
    return redirect(url_for("auth.verify"))


# ---------- login / logout ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("market.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                session["pending_uid"] = user.id
                _send_verification(user)
                flash("Please verify your email first. We sent you a new code.", "info")
                return redirect(url_for("auth.verify"))
            login_user(user, remember=form.remember.data)
            return redirect(_safe_next(request.args.get("next")))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("market.home"))


# ---------- forgot / reset password ----------
@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            link = url_for("auth.reset", token=_make_reset_token(user), _external=True)
            send_templated(user.email, f"Reset your {APP_NAME} password", "Reset your password",
                           [f"Hi {user.username},", "Click the button below to choose a new password."],
                           button_text="Choose new password", button_url=link,
                           footer="This link works for 1 hour. If you didn't ask for it, you can ignore this email.")
        # Same message either way so nobody can check which emails are registered.
        flash("If that email is registered, a reset link is on its way.", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot.html", form=form)


@bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    user = _user_from_reset_token(token)
    if not user:
        flash("That reset link is invalid or has expired. Request a new one.", "error")
        return redirect(url_for("auth.forgot"))
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        send_templated(user.email, f"Your {APP_NAME} password was changed", "Password changed",
                       [f"Hi {user.username},", "Your password was just changed.",
                        "If this wasn't you, reset it again right away."])
        flash("Password changed. You can log in now.", "success")
        return redirect(url_for("auth.login"))
    return render_template("reset.html", form=form)
