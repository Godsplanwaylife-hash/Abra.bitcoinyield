"""CoinGecko price access (public API, cached) and simulated trade settlement."""
import time

import requests

from models import Trade, db, utcnow

COINS = {
    "BTC": {"id": "bitcoin", "name": "Bitcoin", "pair": "BTCUSDT", "tv": "BINANCE:BTCUSDT"},
    "ETH": {"id": "ethereum", "name": "Ethereum", "pair": "ETHUSDT", "tv": "BINANCE:ETHUSDT"},
}

DURATIONS = [60, 180, 300]   # seconds
PAYOUT_RATE = 0.80           # profit on a winning simulated contract
MIN_STAKE = 10.0

_URL = "https://api.coingecko.com/api/v3/coins/markets"
_TTL = 60  # seconds; keeps us well inside CoinGecko's free rate limit
_cache = {"ts": 0.0, "data": {}}


def get_market_data():
    """Return {"BTC": {...}, "ETH": {...}}. Falls back to stale cache, then {}."""
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _TTL:
        return _cache["data"]
    try:
        resp = requests.get(
            _URL,
            params={
                "vs_currency": "usd",
                "ids": ",".join(c["id"] for c in COINS.values()),
                "sparkline": "true",
                "price_change_percentage": "24h",
            },
            timeout=8,
        )
        resp.raise_for_status()
        by_id = {row["id"]: row for row in resp.json()}
        data = {}
        for sym, meta in COINS.items():
            row = by_id.get(meta["id"])
            if not row or row.get("current_price") is None:
                continue
            spark = (row.get("sparkline_in_7d") or {}).get("price") or []
            data[sym] = {
                "price": float(row["current_price"]),
                "change_24h": float(row.get("price_change_percentage_24h") or 0.0),
                "high_24h": row.get("high_24h"),
                "low_24h": row.get("low_24h"),
                "spark": spark[::4],  # hourly -> every 4h, ~42 points
            }
        if data:
            _cache.update(ts=now, data=data)
            return data
    except (requests.RequestException, ValueError, KeyError):
        pass
    return _cache["data"]  # stale data is better than none


def get_price(symbol):
    coin = get_market_data().get(symbol)
    return coin["price"] if coin else None


def spark_points(values, w=100, h=32):
    if not values or len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = w / (len(values) - 1)
    return " ".join(
        f"{i * step:.1f},{h - 2 - ((v - lo) / span) * (h - 4):.1f}"
        for i, v in enumerate(values)
    )


def settle_due_trades(user):
    """Settle expired simulated trades at the latest price. Returns count settled."""
    due = Trade.query.filter(
        Trade.user_id == user.id, Trade.status == "open", Trade.expires_at <= utcnow()
    ).all()
    settled = 0
    for t in due:
        price = get_price(t.symbol)
        if price is None:
            continue  # try again later
        t.exit_price = price
        if price == t.entry_price:
            t.status, t.payout = "draw", t.amount          # stake refunded
        elif (price > t.entry_price) == (t.direction == "up"):
            t.status, t.payout = "won", round(t.amount * (1 + PAYOUT_RATE), 2)
        else:
            t.status, t.payout = "lost", 0.0
        user.demo_balance += t.payout
        settled += 1
    if settled:
        db.session.commit()
    return settled
