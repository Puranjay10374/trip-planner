from datetime import datetime
from extensions import db, bcrypt

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    trips = db.relationship('Trip', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class Trip(db.Model):
    __tablename__ = 'trips'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    budget = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='planned')  # planned, ongoing, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationship with activities
    activities = db.relationship('Activity', back_populates='trip', cascade='all, delete-orphan', lazy=True)
    
    def to_dict(self, include_activities=False):
        trip_dict = {
            'id': self.id,
            'title': self.title,
            'destination': self.destination,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'description': self.description,
            'budget': self.budget,
            'status': self.status,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_activities:
            trip_dict['activities'] = [activity.to_dict() for activity in self.activities]
            trip_dict['activity_count'] = len(self.activities)
            trip_dict['total_activity_cost'] = sum(activity.cost or 0 for activity in self.activities)
        
        return trip_dict


class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    activity_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    cost = db.Column(db.Float, default=0.0)
    category = db.Column(db.String(50))  # sightseeing, dining, adventure, shopping, relaxation, transport, accommodation, other
    booking_reference = db.Column(db.String(100))
    booking_url = db.Column(db.String(500))
    notes = db.Column(db.Text)
    is_booked = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, must-do
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    trip = db.relationship('Trip', back_populates='activities')
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'cost': self.cost,
            'category': self.category,
            'booking_reference': self.booking_reference,
            'booking_url': self.booking_url,
            'notes': self.notes,
            'is_booked': self.is_booked,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
