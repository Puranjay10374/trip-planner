# Trip Planner API

A Flask-based REST API for trip planning with JWT authentication and Swagger documentation.

## Features

- **JWT Authentication**: Secure user authentication with access and refresh tokens
- **Swagger UI**: Interactive API documentation via Flasgger
- **User Management**: Register, login, and manage user profiles
- **Trip Management**: Create, read, update, and delete trips
- **SQLAlchemy ORM**: Database management with SQLite (can be changed to PostgreSQL/MySQL)
- **Database Migrations**: Flask-Migrate for schema version control
- **Blueprint Architecture**: Modular and scalable code structure

## Project Structure

```
trip-planner/
├── app.py                 # Main application entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── models/
│   ├── __init__.py
│   ├── user.py           # User model
│   └── trip.py           # Trip model
├── blueprints/
│   ├── __init__.py
│   ├── auth.py           # Authentication endpoints
│   ├── users.py          # User management endpoints
│   └── trips.py          # Trip management endpoints
└── utils/
    ├── __init__.py
    └── decorators.py     # Custom decorators
```

## Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Initialize database migrations** (First time only):
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

3. **Run the application**:
```bash
python app.py
```

4. **Access the API**:
- API Root: `http://localhost:5000/`
- Swagger UI: `http://localhost:5000/docs/`

> 📚 **For detailed migration commands and workflows**, see [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md)

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT tokens
- `POST /api/auth/refresh` - Refresh access token

### Users
- `GET /api/users/profile` - Get current user profile (requires JWT)
- `DELETE /api/users/profile` - Delete user account (requires JWT)

### Trips
- `GET /api/trips/` - Get all trips for current user (requires JWT)
- `POST /api/trips/` - Create a new trip (requires JWT)
- `GET /api/trips/<trip_id>` - Get specific trip (requires JWT)
- `PUT /api/trips/<trip_id>` - Update trip (requires JWT)
- `DELETE /api/trips/<trip_id>` - Delete trip (requires JWT)

## Usage Examples

### 1. Register a User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### 3. Create a Trip (with JWT token)
```bash
curl -X POST http://localhost:5000/api/trips/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Summer Vacation",
    "destination": "Paris, France",
    "start_date": "2024-07-01",
    "end_date": "2024-07-15",
    "description": "A wonderful trip to Paris",
    "budget": 5000.0,
    "status": "planned"
  }'
```

## Swagger UI Usage

1. Open `http://localhost:5000/docs/` in your browser
2. Click on "Authorize" button (top right)
3. Enter: `Bearer YOUR_ACCESS_TOKEN` (replace with actual token from login)
4. Click "Authorize"
5. Now you can test all protected endpoints directly from Swagger UI

## Database

The application uses SQLite by default (`site.db` file). To use a different database:

1. Set the `DATABASE_URL` environment variable:
```bash
# PostgreSQL
export DATABASE_URL="postgresql://username:password@localhost/dbname"

# MySQL
export DATABASE_URL="mysql://username:password@localhost/dbname"
```

### Database Migrations

This project uses Flask-Migrate to manage database schema changes:

```bash
# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Rollback last migration
flask db downgrade
```

See [MIGRATIONS_GUIDE.md](MIGRATIONS_GUIDE.md) for complete documentation.

## Environment Variables

You can set these environment variables for production:

- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key
- `DATABASE_URL`: Database connection string

## Security Notes

- Change default secret keys in production
- Use HTTPS in production
- Set strong JWT expiration times
- Use environment variables for sensitive data
- Consider rate limiting for production

## Models

### User Model
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `password_hash`: Hashed password
- `created_at`: Account creation timestamp
- `trips`: Relationship to Trip model

### Trip Model
- `id`: Primary key
- `title`: Trip title
- `destination`: Trip destination
- `start_date`: Trip start date
- `end_date`: Trip end date
- `description`: Trip description
- `budget`: Trip budget
- `status`: Trip status (planned, ongoing, completed, cancelled)
- `user_id`: Foreign key to User
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## License

MIT License
