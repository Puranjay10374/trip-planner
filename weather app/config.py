import os
import logging
from logging.handlers import RotatingFileHandler

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your_jwt_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
    # Collaborator Configuration
    MAX_COLLABORATORS_PER_TRIP = 10
    COLLABORATION_INVITE_EXPIRY_DAYS = 7
    
    # Weather API Configuration
    # Using WeatherAPI.com - Get your FREE key at: https://www.weatherapi.com/signup.aspx
    WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY') or 'e5c1ce5fbf0243aeb43105620250111'
    WEATHER_API_BASE_URL = 'https://api.weatherapi.com/v1'
    WEATHER_CACHE_TIMEOUT = 1800  # 30 minutes in seconds
    WEATHER_UNITS = 'metric'  # metric (Celsius), imperial (Fahrenheit)
    
    # Currency Configuration
    DEFAULT_CURRENCY = 'INR'
    SUPPORTED_CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'AUD', 'CAD', 'JPY', 'CNY', 'THB', 'MYR']
    CURRENCY_SYMBOLS = {
        'INR': '₹',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'AED': 'د.إ',
        'SGD': 'S$',
        'AUD': 'A$',
        'CAD': 'C$',
        'JPY': '¥',
        'CNY': '¥',
        'THB': '฿',
        'MYR': 'RM'
    }
    
    # Email Configuration (SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or ('Trip Planner', 'noreply@tripplanner.com')
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False
    
    # Email Templates
    MAIL_SUBJECT_PREFIX = '[Trip Planner]'
    ADMINS = ['admin@tripplanner.com']
    
    # Logging Configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    LOG_LEVEL = logging.DEBUG
    
    # Swagger Configuration
    SWAGGER = {
        'title': 'Trip Planner API',
        'uiversion': 3,
        'description': 'API for managing trip planning with JWT authentication',
        'version': '1.0.0',
        'termsOfService': '',
        'hide_top_bar': False,
        'specs_route': '/docs/'
    }
    
    # Swagger security definitions
    SWAGGER_CONFIG = {
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
            }
        },
        'security': [{'Bearer': []}]
    }
    
    @staticmethod
    def init_app(app):
        """Initialize logging"""
        if not app.debug and not app.testing:
            if app.config['LOG_TO_STDOUT']:
                stream_handler = logging.StreamHandler()
                stream_handler.setLevel(logging.INFO)
                app.logger.addHandler(stream_handler)
            else:
                if not os.path.exists('logs'):
                    os.mkdir('logs')
                file_handler = RotatingFileHandler('logs/tripplanner.log',
                                                    maxBytes=10240000, backupCount=10)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s '
                    '[in %(pathname)s:%(lineno)d]'))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Trip Planner startup')
