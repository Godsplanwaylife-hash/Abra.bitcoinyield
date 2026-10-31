import re

from flask_wtf import FlaskForm
from wtforms import (BooleanField, PasswordField, SelectField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Optional,
                                Regexp, ValidationError)

from models import User

BTC_RE = re.compile(r"^(bc1[a-z0-9]{25,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")
ETH_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


class SignupForm(FlaskForm):
    username = StringField("Username", validators=[
        DataRequired(), Length(3, 32),
        Regexp(r"^[A-Za-z0-9_]+$", message="Letters, numbers and underscores only.")])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(8, 128)])
    confirm = PasswordField("Confirm password", validators=[
        DataRequired(), EqualTo("password", message="Passwords do not match.")])
    submit = SubmitField("Create account")

    def validate_username(self, field):
        if User.query.filter(User.username.ilike(field.data)).first():
            raise ValidationError("That username is taken.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("That email is already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Log in")


class VerifyForm(FlaskForm):
    code = StringField("6-digit code", validators=[
        DataRequired(), Length(6, 6), Regexp(r"^\d{6}$", message="Enter the 6 digits from your email.")])
    submit = SubmitField("Verify")


class ForgotForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send reset link")


class ResetForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(8, 128)])
    confirm = PasswordField("Confirm new password", validators=[
        DataRequired(), EqualTo("password", message="Passwords do not match.")])
    submit = SubmitField("Change password")


class WalletForm(FlaskForm):
    network = SelectField("Network", choices=[("BTC", "Bitcoin (BTC)"), ("ERC20", "Ethereum (ERC-20)")])
    address = StringField("Your wallet address", validators=[Optional(), Length(max=100)])
    submit = SubmitField("Save address")

    def validate_address(self, field):
        value = (field.data or "").strip()
        if not value:
            return
        pattern = BTC_RE if self.network.data == "BTC" else ETH_RE
        if not pattern.match(value):
            raise ValidationError(f"That doesn't look like a valid {self.network.data} address.")


class SupportForm(FlaskForm):
    topic = SelectField("Topic", choices=[
        ("How it works", "How the app works"),
        ("Invest funds", "Invest funds / check balance"),
        ("Trading", "Simulated trading"),
        ("Account", "My account"),
        ("Other", "Something else")])
    message = TextAreaField("Your message", validators=[DataRequired(), Length(10, 2000)])
    submit = SubmitField("Send message")
