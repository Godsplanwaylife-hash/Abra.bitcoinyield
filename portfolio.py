"""Virtual portfolio maths. Holdings are stored as coin units, so their value
moves with the live BTC/ETH price. Nothing here touches real money."""
import math

from services import COINS, get_market_data

ASSETS = ("USDT", "BTC", "ETH")
_UNITS = {"BTC": "btc_units", "ETH": "eth_units"}


def _prices():
    market = get_market_data()
    return {s: market[s]["price"] for s in COINS if s in market}


def _units(user, sym):
    return float(getattr(user, _UNITS[sym]) or 0.0)


def snapshot(user):
    prices = _prices()
    cash = float(user.demo_balance or 0.0)
    btc_u, eth_u = _units(user, "BTC"), _units(user, "ETH")
    has_holdings = btc_u > 0 or eth_u > 0
    price_ok = (btc_u <= 0 or "BTC" in prices) and (eth_u <= 0 or "ETH" in prices)
    btc_value = btc_u * prices.get("BTC", 0.0)
    eth_value = eth_u * prices.get("ETH", 0.0)
    holdings = btc_value + eth_value
    basis = float(user.cost_basis or 0.0)
    live = has_holdings and price_ok
    change = holdings - basis if live else 0.0
    pct = change / basis * 100 if (live and basis > 0) else 0.0
    return {
        "cash": cash, "btc_units": btc_u, "eth_units": eth_u,
        "btc_value": btc_value, "eth_value": eth_value, "holdings": holdings,
        "total": cash + holdings, "cost_basis": basis,
        "change": change, "change_pct": pct,
        "has_holdings": has_holdings, "price_ok": price_ok,
    }


def convert_assets(user, src, dst, usd):
    """Move `usd` worth of value from src to dst. Returns an error string or None."""
    if src not in ASSETS or dst not in ASSETS or src == dst:
        return "Choose two different assets."
    if not math.isfinite(usd) or usd < 1:
        return "Minimum conversion is 1 USDT."
    prices = _prices()
    for sym in (src, dst):
        if sym != "USDT" and sym not in prices:
            return "Live prices are unavailable right now. Try again shortly."

    holdings_before = snapshot(user)["holdings"]
    avail = float(user.demo_balance) if src == "USDT" else _units(user, src) * prices[src]
    if usd > avail + 0.005:
        return f"Not enough {src}. You have {avail:,.2f} USDT worth."

    basis = float(user.cost_basis or 0.0)

    # take from the source
    if src == "USDT":
        user.demo_balance = max(0.0, float(user.demo_balance) - usd)
    else:
        left = _units(user, src) - usd / prices[src]
        sold_all = usd >= avail - 0.005 or left < 1e-12
        setattr(user, _UNITS[src], 0.0 if sold_all else left)

    # give to the destination
    if dst == "USDT":
        user.demo_balance = float(user.demo_balance) + usd
    else:
        setattr(user, _UNITS[dst], _units(user, dst) + usd / prices[dst])

    # cost basis (average cost across the whole portfolio)
    if src == "USDT":
        basis += usd
    elif dst == "USDT" and holdings_before > 0:
        basis -= basis * min(1.0, usd / holdings_before)
    still_holding = _units(user, "BTC") > 0 or _units(user, "ETH") > 0
    user.cost_basis = max(0.0, basis) if still_holding else 0.0
    return None
