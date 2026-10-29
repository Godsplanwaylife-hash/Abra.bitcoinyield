import math
import os
import time

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from emailer import APP_NAME, send_templated
from forms import SupportForm, WalletForm
from models import STARTING_BALANCE, Trade, db
from services import get_market_data, settle_due_trades

bp = Blueprint("market", __name__)

MIN_TOPUP = 10           # virtual USDT only
MAX_TOPUP = 10_000
MAX_DEMO_BALANCE = 100_000


@bp.route("/")
def home():
    return render_template("home.html", market=get_market_data())


@bp.route("/market")
def market():
    return render_template("market.html", market=get_market_data())


@bp.route("/assets")
@login_required
def assets():
    settle_due_trades(current_user)
    trades = current_user.trades.order_by(Trade.opened_at.desc()).limit(50).all()
    closed = current_user.trades.filter(Trade.status != "open")
    stats = {
        "open": current_user.trades.filter_by(status="open").count(),
        "won": closed.filter_by(status="won").count(),
        "lost": closed.filter_by(status="lost").count(),
        "net": db.session.query(func.coalesce(func.sum(Trade.payout - Trade.amount), 0.0))
                 .filter(Trade.user_id == current_user.id, Trade.status != "open").scalar(),
    }
    return render_template("assets.html", trades=trades, stats=stats, start=STARTING_BALANCE)


@bp.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Adds VIRTUAL demo USDT. No real crypto is involved."""
    if request.method == "POST":
        try:
            amount = round(float(request.form.get("amount", "")), 2)
        except ValueError:
            amount = float("nan")
        if not math.isfinite(amount) or not (MIN_TOPUP <= amount <= MAX_TOPUP):
            flash(f"Enter an amount between {MIN_TOPUP:,} and {MAX_TOPUP:,} USDT.", "error")
        elif current_user.demo_balance + amount > MAX_DEMO_BALANCE:
            flash(f"Demo balance can't go above {MAX_DEMO_BALANCE:,} USDT.", "error")
        else:
            current_user.demo_balance += amount
            db.session.commit()
            flash(f"Added {amount:,.2f} virtual USDT to your demo balance.", "success")
            return redirect(url_for("market.assets"))
    return render_template("deposit.html", min_amount=MIN_TOPUP, max_amount=MAX_TOPUP,
                       max_balance=MAX_DEMO_BALANCE)

@bp.route("/support", methods=["GET", "POST"])
@login_required
def support():
    form = SupportForm()
    if form.validate_on_submit():
        if time.time() - session.get("last_support", 0) < 60:
            flash("Please wait a minute before sending another message.", "error")
        else:
            to = os.environ.get("SUPPORT_EMAIL") or os.environ.get("MAIL_USERNAME") or "support@example.com"
            send_templated(
                to, f"[{APP_NAME} support] {form.topic.data} from {current_user.username}",
                "New support message",
                [f"From: {current_user.username} <{current_user.email}>",
                 f"Topic: {form.topic.data}", form.message.data],
                footer="Reply to this email to answer the user directly.",
                reply_to=current_user.email,
            )
            send_templated(
                current_user.email, f"We got your message - {APP_NAME} support",
                "We got your message",
                [f"Hi {current_user.username},",
                 "Thanks for reaching out. We'll reply to this email address.",
                 "Your message:", form.message.data],
            )
            session["last_support"] = time.time()
            flash("Message sent. We'll reply to your email.", "success")
            return redirect(url_for("market.support"))
    return render_template("support.html", form=form)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = WalletForm(network=current_user.wallet_network or "BTC",
                      address=current_user.wallet_address or "")
    if form.validate_on_submit():
        address = (form.address.data or "").strip()
        current_user.wallet_address = address or None
        current_user.wallet_network = form.network.data if address else None
        db.session.commit()
        flash("Reference address saved." if address else "Reference address removed.", "success")
        return redirect(url_for("market.profile"))
    return render_template("profile.html", form=form)


@bp.route("/profile/reset-demo", methods=["POST"])
@login_required
def reset_demo():
    Trade.query.filter_by(user_id=current_user.id).delete()
    current_user.demo_balance = STARTING_BALANCE
    db.session.commit()
    flash("Demo balance reset to 0 and trade history cleared.", "success")
    return redirect(url_for("market.profile"))
