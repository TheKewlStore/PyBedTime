from flask_sqlalchemy import SQLAlchemy

from flask import current_app


_db = SQLAlchemy()


def initialize():
    _db.init_app(current_app)


def instance():
    return _db
