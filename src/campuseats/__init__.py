from flask import Flask
from sqlalchemy import text
from campuseats.config import Config
from campuseats.routes.main import main_bp
from campuseats.routes.student import student_bp
from campuseats.extensions import db, login_manager
from campuseats.models import DietaryTag, Listing, Reservation, User
from campuseats.routes.auth import auth_bp
from campuseats.routes.vendor import vendor_bp
from campuseats.seed import seed_database


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    # Redirect to login page if user is not authenticated
    login_manager.login_view = "auth.login"

    # Define the user loader function for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return None

        return db.session.get(User, user_id)

    app.register_blueprint(main_bp)
    # include the auth blueprint for authentication routes
    app.register_blueprint(auth_bp)
    # include the vendor blueprint for vendor routes
    app.register_blueprint(vendor_bp)
    # include the student blueprint for student browse and reservation routes
    app.register_blueprint(student_bp)

    with app.app_context():
        db.session.execute(text("SELECT 1"))  # fails loudly if the DB is unreachable
        db.create_all()  # builds tables for any models (none exist yet)
        if db.engine.dialect.name == "postgresql":
            db.session.execute(
                text(
                    "ALTER TABLE reservations ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(100)"
                )
            )
            db.session.commit()
        if app.config.get("SEED_DEMO_USERS"):
            seed_database()

    return app
