from flask import Blueprint, render_template
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from campuseats.extensions import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.get("/health/db")
def health_db():
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return {"status": "error"}, 500
    return {"status": "ok"}, 200
