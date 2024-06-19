from flask import Flask, current_app
from flask.helpers import url_for
from flask_sqlalchemy import SQLAlchemy
from os import environ
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from config.config import DevelopmentConfig, ProductionConfig, StagingConfig  # Import all configs
import os


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

    print("config")

    app.config.from_object(config_class)  # Load the appropriate config class

    # # Load configuration based on environment
    # env_config = environ.get('APP_SETTINGS') or 'DevelopmentConfig'  # Default to development
    # if env_config == 'DevelopmentConfig':
    #     app.config.from_object('instance.config.DevelopmentConfig')
    # elif env_config == 'StagingConfig':
    #     app.config.from_object('instance.config.StagingConfig')
    # elif env_config == 'Config':
    #     app.config.from_object('instance.config.ProductionConfig')
    # else:
    #     raise ValueError(f'Invalid environment: {env_config}')
    


    # app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    # app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    # mail config: 
    
    # app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    # app.config['MAIL_PORT'] = 465
    # app.config["MAIL_USE_TLS"]= False
    # app.config['MAIL_USE_SSL'] = True
    # app.config['MAIL_USERNAME'] = 'info.reportthatpantry@gmail.com'
    # app.config['MAIL_PASSWORD'] = 'vrucxrsmpacwcdsk'
    
    # email = Mail(app)


    
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