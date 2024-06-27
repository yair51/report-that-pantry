import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    TESTING = False
    FLASK_APP = "main.py"
    SECRET_KEY = os.getenv("SECRET_KEY")  # No default; this should always be set externally
    SQLALCHEMY_DATABASE_URI = "postgresql" + os.getenv("DATABASE_URL")[8:]  # Include +psycopg2
    SQLALCHEMY_TRACK_MODIFICATIONS = False
     # Email
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')  # SendGrid as default
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))  # SendGrid's default port
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'apikey')  # SendGrid uses 'apikey'
    MAIL_PASSWORD = os.environ.get('SENDGRID_API_KEY')  # SendGrid API key
    # File Uploads (S3)
    S3_BUCKET = os.environ.get('S3_BUCKET')
    S3_KEY = os.environ.get('S3_KEY')
    S3_SECRET = os.environ.get('S3_SECRET')
    S3_LOCATION = f'http://{S3_BUCKET}.s3.amazonaws.com/'
    # TODO - handle oversized uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit (adjust as needed)


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False


class StagingConfig(Config):
    FLASK_ENV = 'staging'
    DEBUG = True


class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///database.db")
