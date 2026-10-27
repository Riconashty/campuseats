from flask import Flask
from sqlalchemy import text
from campuseats.config import Config
from campuseats.routes.main import main_bp
from campuseats.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    app.register_blueprint(main_bp)

    with app.app_context():
        db.session.execute(text("SELECT 1"))  # fails loudly if the DB is unreachable
        db.create_all()  # builds tables for any models (none exist yet)

    return app