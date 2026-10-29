import os

from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from models import User, db
from services import COINS, spark_points

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"
csrf = CSRFProtect()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///" + os.path.join(app.instance_path, "dashboard.db")),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)  # render_as_batch: needed for SQLite
    login_manager.init_app(app)
    csrf.init_app(app)

    from routes.auth import bp as auth_bp
    from routes.contract import bp as contract_bp
    from routes.market import bp as market_bp
    app.register_blueprint(market_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(contract_bp)

    app.jinja_env.filters["spark_points"] = spark_points
    app.jinja_env.filters["money"] = lambda v: f"{v:,.2f}"

    @app.context_processor
    def inject_globals():
        return {"COINS": COINS}

    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="Page not found."), 404

    # No db.create_all() here: tables are created by migrations (flask db upgrade).
    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


if __name__ == "__main__":
    create_app().run(debug=True)