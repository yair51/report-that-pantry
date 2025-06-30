from flask import Flask, current_app
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from os import environ
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from config.config import DevelopmentConfig, ProductionConfig, StagingConfig  # Import all configs
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
DB_NAME = "database.db"


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # Determine the config class based on the environment
    config_class = {
        'production': ProductionConfig,
        'development': DevelopmentConfig,
        'staging': StagingConfig,
    }.get(os.environ.get('FLASK_ENV'), DevelopmentConfig)  # Default to DevelopmentConfig

    import ssl

    import certifi

    os.environ['SSL_CERT_FILE'] = certifi.where()
    ssl._create_default_https_context = ssl._create_unverified_context

    app.config.from_object(config_class)  # Load the appropriate config class


    
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    from .models import User, Location, Report

    create_database(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app


def create_database(app):
    # if not path.exists('website/' + DB_NAME):
    db.create_all(app=app)
    print('Created Database!')