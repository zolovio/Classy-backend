import os

database_name = os.getenv("DATABASE_NAME")
database_username = os.getenv("DATABASE_USERNAME")
database_password = os.getenv("DATABASE_PASSWORD")
host = os.getenv("HOST")

# set database url
database_path = "mysql://{}:{}@{}/{}".format(
    database_username, database_password, host, database_name
)
# database_path = "sqlite:///db.sqlite3"
# database_path = "postgresql://postgres:postgres@127.0.0.1:5432/classy"


class Config:
    """Base configuration"""
    TESTING = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = database_path
    SECRET_KEY = "app_secret"
    DEBUG_TB_ENABLED = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    BCRYPT_LOG_ROUNDS = 13
    TOKEN_EXPIRATION_DAYS = 1
    TOKEN_EXPIRATION_SECONDS = 0
