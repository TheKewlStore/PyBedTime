class DefaultConfiguration(object):
    APPLICATION_NAME = "HTe Device Management"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "HTE-Secret"
    SECURITY_PASSWORD_SALT = "password-salt-hte-09/04"
