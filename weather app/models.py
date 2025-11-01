from datetime import datetime
from extensions import db, bcrypt
import enum


class CollaboratorRole(enum.Enum):
    """Enum for collaborator roles"""
    OWNER = 'owner'
    EDITOR = 'editor'
    VIEWER = 'viewer'


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


class TripCollaborator(db.Model):
    """Model for trip collaborators"""
    __tablename__ = 'trip_collaborators'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Enum(CollaboratorRole), default=CollaboratorRole.VIEWER, nullable=False)
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, accepted, rejected
    
    # Relationships
    trip = db.relationship('Trip', backref='collaborators', foreign_keys=[trip_id])
    user = db.relationship('User', foreign_keys=[user_id], backref='trip_collaborations')
    inviter = db.relationship('User', foreign_keys=[invited_by])
    
    # Unique constraint to prevent duplicate collaborators
    __table_args__ = (
        db.UniqueConstraint('trip_id', 'user_id', name='unique_trip_collaborator'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'email': self.user.email if self.user else None,
            'role': self.role.value,
            'status': self.status,
            'invited_by': self.invited_by,
            'inviter_username': self.inviter.username if self.inviter else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None
        }


class DayPlan(db.Model):
    """Daily itinerary for a trip"""
    __tablename__ = 'day_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    day_number = db.Column(db.Integer)  # Day 1, Day 2, etc.
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodations.id'))
    total_distance = db.Column(db.Float)  # km traveled that day
    estimated_cost = db.Column(db.Float)
    notes = db.Column(db.Text)
    is_rest_day = db.Column(db.Boolean, default=False)
    weather_checked = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trip = db.relationship('Trip', backref=db.backref('day_plans', cascade='all, delete-orphan', order_by='DayPlan.date'))
    accommodation = db.relationship('Accommodation', backref='day_plans')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'date': self.date.isoformat() if self.date else None,
            'day_number': self.day_number,
            'title': self.title,
            'description': self.description,
            'accommodation_id': self.accommodation_id,
            'total_distance': self.total_distance,
            'estimated_cost': self.estimated_cost,
            'notes': self.notes,
            'is_rest_day': self.is_rest_day,
            'weather_checked': self.weather_checked,
            'activity_count': len(self.activities) if hasattr(self, 'activities') else 0,
            'activities': [activity.to_dict() for activity in self.activities] if hasattr(self, 'activities') else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Accommodation(db.Model):
    """Accommodation/lodging for trips"""
    __tablename__ = 'accommodations'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50))  # hotel, hostel, airbnb, resort, apartment, house
    address = db.Column(db.String(500))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=False)
    confirmation_number = db.Column(db.String(100))
    cost_per_night = db.Column(db.Float)
    total_cost = db.Column(db.Float)
    currency = db.Column(db.String(3), default='USD')
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(100))
    booking_url = db.Column(db.String(500))
    rating = db.Column(db.Float)
    amenities = db.Column(db.JSON)  # ["wifi", "pool", "breakfast", "parking"]
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    trip = db.relationship('Trip', backref=db.backref('accommodations', cascade='all, delete-orphan'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'name': self.name,
            'type': self.type,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'check_in': self.check_in.isoformat() if self.check_in else None,
            'check_out': self.check_out.isoformat() if self.check_out else None,
            'confirmation_number': self.confirmation_number,
            'cost_per_night': self.cost_per_night,
            'total_cost': self.total_cost,
            'currency': self.currency,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'booking_url': self.booking_url,
            'rating': self.rating,
            'amenities': self.amenities,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Activity(db.Model):
    """Individual activities/events in the itinerary"""
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    day_plan_id = db.Column(db.Integer, db.ForeignKey('day_plans.id', ondelete='CASCADE'))
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='other')  # sightseeing, food, transport, adventure, relaxation, shopping, culture, nightlife, other
    
    # Location
    location = db.Column(db.String(200))
    address = db.Column(db.String(500))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    
    # Timing
    activity_date = db.Column(db.Date)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    duration_minutes = db.Column(db.Integer)
    all_day = db.Column(db.Boolean, default=False)
    
    # Priority & Status
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, must_do
    status = db.Column(db.String(20), default='planned')  # planned, booked, in_progress, completed, cancelled, skipped
    
    # Booking Information
    booking_required = db.Column(db.Boolean, default=False)
    booking_url = db.Column(db.String(500))
    booking_reference = db.Column(db.String(100))
    booking_status = db.Column(db.String(20))  # not_needed, pending, confirmed, cancelled
    
    # Financial
    cost = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    paid = db.Column(db.Boolean, default=False)
    
    # Contact & Details
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(100))
    website = db.Column(db.String(500))
    
    # Review & Feedback (after completion)
    rating = db.Column(db.Integer)  # 1-5 stars
    review = db.Column(db.Text)
    photos = db.Column(db.JSON)  # Array of photo URLs
    
    # Additional
    notes = db.Column(db.Text)
    weather_dependent = db.Column(db.Boolean, default=False)
    indoor = db.Column(db.Boolean, default=False)
    accessibility = db.Column(db.String(100))  # wheelchair_accessible, stairs, etc.
    age_restriction = db.Column(db.String(50))
    dress_code = db.Column(db.String(100))
    tags = db.Column(db.JSON)  # ["family-friendly", "romantic", "adventure"]
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    day_plan = db.relationship('DayPlan', backref=db.backref('activities', cascade='all, delete-orphan', order_by='Activity.start_time'))
    trip = db.relationship('Trip', back_populates='activities')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'day_plan_id': self.day_plan_id,
            'trip_id': self.trip_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'location': self.location,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'all_day': self.all_day,
            'priority': self.priority,
            'status': self.status,
            'booking_required': self.booking_required,
            'booking_url': self.booking_url,
            'booking_reference': self.booking_reference,
            'booking_status': self.booking_status,
            'cost': self.cost,
            'currency': self.currency,
            'paid': self.paid,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'website': self.website,
            'rating': self.rating,
            'review': self.review,
            'photos': self.photos,
            'notes': self.notes,
            'weather_dependent': self.weather_dependent,
            'indoor': self.indoor,
            'accessibility': self.accessibility,
            'age_restriction': self.age_restriction,
            'dress_code': self.dress_code,
            'tags': self.tags,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
