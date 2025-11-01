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
    currency = db.Column(db.String(3), default='INR')
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
    currency = db.Column(db.String(3), default='INR')
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


class BudgetCategory(db.Model):
    """Budget categories for expense tracking"""
    __tablename__ = 'budget_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Accommodation, Food, Transport, Activities, Shopping, etc.
    allocated_amount = db.Column(db.Float, nullable=False, default=0.0)
    spent_amount = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='INR')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trip = db.relationship('Trip', backref=db.backref('budget_categories', lazy=True, cascade='all, delete-orphan'))
    expenses = db.relationship('Expense', backref='budget_category_rel', lazy=True, foreign_keys='Expense.category_id')
    
    @property
    def remaining_amount(self):
        """Calculate remaining budget"""
        return self.allocated_amount - self.spent_amount
    
    @property
    def percentage_used(self):
        """Calculate percentage of budget used"""
        if self.allocated_amount == 0:
            return 0.0
        return (self.spent_amount / self.allocated_amount) * 100
    
    @property
    def is_over_budget(self):
        """Check if category is over budget"""
        return self.spent_amount > self.allocated_amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'category': self.category,
            'allocated_amount': self.allocated_amount,
            'spent_amount': self.spent_amount,
            'remaining_amount': self.remaining_amount,
            'percentage_used': round(self.percentage_used, 2),
            'is_over_budget': self.is_over_budget,
            'currency': self.currency,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Expense(db.Model):
    """Expense records for trips"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('budget_categories.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='INR')
    
    # Expense details
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50))  # Cash, Credit Card, Debit Card, etc.
    receipt_url = db.Column(db.String(500))
    vendor_name = db.Column(db.String(200))
    location = db.Column(db.String(200))
    
    # Split information
    is_split = db.Column(db.Boolean, default=False)
    split_type = db.Column(db.String(20), default='equal')  # equal, percentage, custom
    
    # Status tracking
    is_settled = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trip = db.relationship('Trip', backref=db.backref('expenses', lazy=True, cascade='all, delete-orphan'))
    payer = db.relationship('User', backref='expenses_paid', foreign_keys=[paid_by])
    splits = db.relationship('ExpenseSplit', backref='expense', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_splits_amount(self):
        """Calculate total amount from splits"""
        return sum(split.amount for split in self.splits)
    
    @property
    def unsettled_amount(self):
        """Calculate amount not yet settled"""
        return sum(split.amount for split in self.splits if not split.is_paid)
    
    def to_dict(self, include_splits=True):
        data = {
            'id': self.id,
            'trip_id': self.trip_id,
            'category_id': self.category_id,
            'category_name': self.budget_category_rel.category if self.category_id else None,
            'title': self.title,
            'description': self.description,
            'amount': self.amount,
            'currency': self.currency,
            'paid_by': self.paid_by,
            'payer_name': self.payer.username if self.payer else None,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'payment_method': self.payment_method,
            'receipt_url': self.receipt_url,
            'vendor_name': self.vendor_name,
            'location': self.location,
            'is_split': self.is_split,
            'split_type': self.split_type,
            'is_settled': self.is_settled,
            'total_splits_amount': self.total_splits_amount,
            'unsettled_amount': self.unsettled_amount,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_splits:
            data['splits'] = [split.to_dict() for split in self.splits]
        
        return data


class ExpenseSplit(db.Model):
    """Split details for expenses among collaborators"""
    __tablename__ = 'expense_splits'
    
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float)  # If split by percentage
    is_paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='expense_splits')
    
    def to_dict(self):
        return {
            'id': self.id,
            'expense_id': self.expense_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'amount': self.amount,
            'percentage': self.percentage,
            'is_paid': self.is_paid,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Settlement(db.Model):
    """Track settlements between users for a trip"""
    __tablename__ = 'settlements'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='INR')
    is_settled = db.Column(db.Boolean, default=False)
    settled_at = db.Column(db.DateTime)
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trip = db.relationship('Trip', backref=db.backref('settlements', lazy=True, cascade='all, delete-orphan'))
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref='settlements_owed')
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref='settlements_due')
    
    def to_dict(self):
        return {
            'id': self.id,
            'trip_id': self.trip_id,
            'from_user_id': self.from_user_id,
            'from_username': self.from_user.username if self.from_user else None,
            'to_user_id': self.to_user_id,
            'to_username': self.to_user.username if self.to_user else None,
            'amount': self.amount,
            'currency': self.currency,
            'is_settled': self.is_settled,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
