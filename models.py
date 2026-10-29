import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

STARTING_BALANCE = 0.0  # new accounts start empty; funds are added on the Add funds page
CODE_MINUTES = 10
MAX_CODE_ATTEMPTS = 5


def utcnow():
    """Naive UTC timestamp (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    demo_balance = db.Column(db.Float, nullable=False, default=STARTING_BALANCE)
    # Optional, reference-only. Never used to send or receive anything.
    wallet_network = db.Column(db.String(10), nullable=True)  # "BTC" or "ERC20"
    wallet_address = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    # Email verification
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    verify_code_hash = db.Column(db.String(256), nullable=True)
    verify_expires = db.Column(db.DateTime, nullable=True)
    verify_attempts = db.Column(db.Integer, nullable=False, default=0)

    trades = db.relationship("Trade", backref="user", lazy="dynamic",
                             cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_verify_code(self):
        """Create a new 6-digit code, store only its hash, return the plain code."""
        code = f"{secrets.randbelow(10**6):06d}"
        self.verify_code_hash = generate_password_hash(code)
        self.verify_expires = utcnow() + timedelta(minutes=CODE_MINUTES)
        self.verify_attempts = 0
        return code

    def code_sent_seconds_ago(self):
        if not self.verify_expires:
            return 10**9
        sent = self.verify_expires - timedelta(minutes=CODE_MINUTES)
        return (utcnow() - sent).total_seconds()

    def check_verify_code(self, code):
        if not self.verify_code_hash or not self.verify_expires:
            return False
        if utcnow() > self.verify_expires or self.verify_attempts >= MAX_CODE_ATTEMPTS:
            return False
        self.verify_attempts += 1
        return check_password_hash(self.verify_code_hash, code)


class Trade(db.Model):
    """A simulated up/down contract. Only touches User.demo_balance."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    symbol = db.Column(db.String(10), nullable=False)       # BTC / ETH
    direction = db.Column(db.String(4), nullable=False)     # up / down
    amount = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    duration = db.Column(db.Integer, nullable=False)        # seconds
    opened_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="open")  # open/won/lost/draw
    payout = db.Column(db.Float, nullable=False, default=0.0)
