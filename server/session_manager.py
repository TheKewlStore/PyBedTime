from flask import current_app


def get_user_datastore():
    return current_app.config["USER_DATASTORE"]


def set_user_datastore(user_datastore):
    current_app.config["USER_DATASTORE"] = user_datastore


def get_database():
    return current_app.config["SQLALCHEMY_INSTANCE"]


def set_database(db):
    current_app.config["SQLALCHEMY_INSTANCE"] = db


def get_security_manager():
    return current_app.config["SECURITY_MANAGER"]


def set_security_manager(manager):
    current_app.config["SECURITY_MANAGER"] = manager
