import json

from flask_security import SQLAlchemyUserDatastore, Security
from flask_security.core import current_user

from server import database

from flask import Flask

from server.default_configuration import DefaultConfiguration

from server import session_manager
from server.models import User, Role


app = Flask(DefaultConfiguration.APPLICATION_NAME)
app.config.from_object(DefaultConfiguration)

with app.app_context():
    database.initialize()

    session_manager.set_database(database.instance())

    user_datastore = SQLAlchemyUserDatastore(session_manager.get_database(), User, Role)
    security = Security(app, user_datastore)

    session_manager.set_user_datastore(user_datastore)
    session_manager.set_security_manager(security)


@app.before_first_request
def create_user():
    session_manager.get_database().create_all()
    session_manager.get_user_datastore().create_user(email='admin', password='admin')
    session_manager.get_database().session.commit()


@app.route('/')
def home():
    if not current_user.is_authenticated:
        return json.dumps({
            "Error": "Unauthorized access!"
        })

    else:
        return json.dumps({
            "Test": "Test"
        })


if __name__ == "__main__":
    app.run()
