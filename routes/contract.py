from datetime import timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Trade, db, utcnow
from services import (COINS, DURATIONS, MIN_STAKE, PAYOUT_RATE, get_market_data,
                      get_price, settle_due_trades)

bp = Blueprint("contract", __name__, url_prefix="/contract")


@bp.route("/")
@login_required
def contract():
    symbol = request.args.get("symbol", "BTC").upper()
    if symbol not in COINS:
        symbol = "BTC"
    settle_due_trades(current_user)
    open_trades = (current_user.trades.filter_by(status="open")
                   .order_by(Trade.expires_at).all())
    return render_template(
        "contract.html", symbol=symbol, coin=COINS[symbol],
        market=get_market_data(), open_trades=open_trades,
        durations=DURATIONS, payout_rate=PAYOUT_RATE, min_stake=MIN_STAKE)


@bp.route("/api/price")
@login_required
def api_price():
    symbol = request.args.get("symbol", "BTC").upper()
    price = get_price(symbol) if symbol in COINS else None
    return jsonify(price=price)


@bp.route("/trade", methods=["POST"])
@login_required
def trade():
    data = request.get_json(silent=True) or {}
    symbol = str(data.get("symbol", "")).upper()
    direction = data.get("direction")
    try:
        amount = round(float(data.get("amount")), 2)
        duration = int(data.get("duration"))
    except (TypeError, ValueError):
        return jsonify(error="Enter a valid amount."), 400

    if symbol not in COINS or direction not in ("up", "down") or duration not in DURATIONS:
        return jsonify(error="Invalid trade settings."), 400
    if amount < MIN_STAKE:
        return jsonify(error=f"Minimum stake is {MIN_STAKE:.0f} USDT."), 400
    if amount > current_user.demo_balance:
        return jsonify(error="Not enough cash balance. Convert some holdings to USDT on the Assets page."), 400

    price = get_price(symbol)
    if price is None:
        return jsonify(error="Live price unavailable right now. Try again shortly."), 503

    now = utcnow()
    current_user.demo_balance -= amount
    db.session.add(Trade(
        user_id=current_user.id, symbol=symbol, direction=direction, amount=amount,
        entry_price=price, duration=duration, opened_at=now,
        expires_at=now + timedelta(seconds=duration)))
    db.session.commit()
    return jsonify(ok=True, balance=current_user.demo_balance, entry_price=price)


@bp.route("/settle", methods=["POST"])
@login_required
def settle():
    count = settle_due_trades(current_user)
    return jsonify(settled=count, balance=current_user.demo_balance)
