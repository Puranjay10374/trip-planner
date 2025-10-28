import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your_jwt_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days
    
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
