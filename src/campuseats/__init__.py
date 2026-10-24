from flask import Flask
from campuseats.config import Config
from campuseats.routes.main import main_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.register_blueprint(main_bp)

    return app
