from flask import Flask
from flasgger import Swagger
from config import Config
from extensions import db, bcrypt, jwt, migrate

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(trips_bp, url_prefix='/api/trips')
    app.register_blueprint(activities_bp, url_prefix='/api')
    
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
    app.run(debug=True)
