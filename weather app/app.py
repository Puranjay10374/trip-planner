from flask import Flask
from flasgger import Swagger
from config import Config
from extensions import db, bcrypt, jwt, migrate, mail
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Set up console logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Verify API key is loaded
    api_key = app.config.get('WEATHER_API_KEY', '')
    print("\n" + "="*60)
    print("🌍 Trip Planner API - Configuration Check")
    print("="*60)
    
    if api_key and len(api_key) > 10:
        print(f"✅ Weather API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"✅ API Key Length: {len(api_key)} characters")
    else:
        print("❌ Weather API Key: NOT LOADED!")
        print(f"❌ Current value: {api_key}")
    
    print(f"✅ Base URL: {app.config['WEATHER_API_BASE_URL']}")
    print(f"✅ Units: {app.config['WEATHER_UNITS']}")
    print("="*60 + "\n")
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Initialize Swagger
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/"
    }
    
    swagger_template = {
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header. Example: 'Bearer {token}'"
            }
        },
        "security": [{"Bearer": []}]
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Register blueprints - import inside app context to avoid circular imports
    from blueprints.auth import auth_bp
    from blueprints.users import users_bp
    from blueprints.trips import trips_bp
    from blueprints.activities import activities_bp
    from blueprints.collaborators import collaborators_bp
    from blueprints.expenses import expenses_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(trips_bp, url_prefix='/api/trips')
    app.register_blueprint(activities_bp, url_prefix='/api')
    app.register_blueprint(collaborators_bp, url_prefix='/api')
    app.register_blueprint(expenses_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        # Import models here so they are registered with SQLAlchemy
        import models
        db.create_all()
    
    @app.route('/')
    def index():
        return {
            'message': 'Welcome to Trip Planner API',
            'documentation': '/docs/'
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("🚀 Starting Trip Planner API Server")
    print("="*60)
    print(f"📍 API: http://127.0.0.1:5000")
    print(f"📚 Docs: http://127.0.0.1:5000/docs/")
    print(f"🌤️  Weather: Enabled (WeatherAPI.com)")
    print(f"📅 Activities & Day Plans: Enabled")
    print(f"👥 Collaborators: Enabled")
    print(f"💰 Budget & Expenses: Enabled")
    print(f"💵 Default Currency: INR (₹)")
    
    # Check email configuration
    if app.config.get('MAIL_USERNAME'):
        print(f"📧 Email: Enabled ({app.config['MAIL_SERVER']})")
    else:
        print(f"📧 Email: Disabled (Configure MAIL_USERNAME in .env)")
    
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
