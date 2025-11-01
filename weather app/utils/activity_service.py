from datetime import datetime, timedelta, time
from flask import current_app
from extensions import db
from models import Activity, DayPlan, Trip
import logging

logger = logging.getLogger(__name__)

class ActivityService:
    """Service for managing activities and day plans"""
    
    @staticmethod
    def create_day_plan(trip_id, date, data):
        """Create a day plan for a trip"""
        try:
            trip = Trip.query.get(trip_id)
            if not trip:
                return None, {'error': 'Trip not found'}, 404
            
            # Validate date is within trip
            if date < trip.start_date or date > trip.end_date:
                return None, {'error': 'Date must be within trip dates'}, 400
            
            # Calculate day number
            day_number = (date - trip.start_date).days + 1
            
            # Check if day plan already exists
            existing = DayPlan.query.filter_by(trip_id=trip_id, date=date).first()
            if existing:
                return None, {'error': 'Day plan already exists for this date'}, 400
            
            day_plan = DayPlan(
                trip_id=trip_id,
                date=date,
                day_number=day_number,
                title=data.get('title', f'Day {day_number}'),
                description=data.get('description'),
                accommodation_id=data.get('accommodation_id'),
                total_distance=data.get('total_distance'),
                estimated_cost=data.get('estimated_cost'),
                notes=data.get('notes'),
                is_rest_day=data.get('is_rest_day', False),
                created_by=data.get('user_id')
            )
            
            db.session.add(day_plan)
            db.session.commit()
            
            return day_plan.to_dict(), None, 201
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating day plan: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def get_trip_itinerary(trip_id):
        """Get complete itinerary for a trip"""
        try:
            trip = Trip.query.get(trip_id)
            if not trip:
                return None, {'error': 'Trip not found'}, 404
            
            day_plans = DayPlan.query.filter_by(trip_id=trip_id).order_by(DayPlan.date).all()
            
            # Get activities not assigned to day plans
            unassigned_activities = Activity.query.filter_by(
                trip_id=trip_id,
                day_plan_id=None
            ).all()
            
            itinerary = {
                'trip_id': trip_id,
                'trip_title': trip.title,
                'destination': trip.destination,
                'start_date': trip.start_date.isoformat(),
                'end_date': trip.end_date.isoformat(),
                'duration_days': (trip.end_date - trip.start_date).days + 1,
                'day_plans': [dp.to_dict() for dp in day_plans],
                'unassigned_activities': [a.to_dict() for a in unassigned_activities],
                'statistics': ActivityService._calculate_itinerary_stats(trip_id)
            }
            
            return itinerary, None, 200
        
        except Exception as e:
            logger.error(f"Error getting itinerary: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def create_activity(trip_id, data):
        """Create a new activity"""
        try:
            trip = Trip.query.get(trip_id)
            if not trip:
                return None, {'error': 'Trip not found'}, 404
            
            # Validate required fields
            if 'title' not in data:
                return None, {'error': 'Title is required'}, 400
            
            # Parse date and time
            activity_date = None
            if 'activity_date' in data:
                activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
                if activity_date < trip.start_date or activity_date > trip.end_date:
                    return None, {'error': 'Activity date must be within trip dates'}, 400
            
            start_time = None
            if 'start_time' in data and data['start_time']:
                start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            
            end_time = None
            if 'end_time' in data and data['end_time']:
                end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            
            # Calculate duration
            duration = data.get('duration_minutes')
            if not duration and start_time and end_time:
                start_dt = datetime.combine(datetime.today(), start_time)
                end_dt = datetime.combine(datetime.today(), end_time)
                duration = int((end_dt - start_dt).total_seconds() / 60)
            
            activity = Activity(
                trip_id=trip_id,
                day_plan_id=data.get('day_plan_id'),
                title=data['title'],
                description=data.get('description'),
                category=data.get('category', 'other'),
                location=data.get('location'),
                address=data.get('address'),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                activity_date=activity_date,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                all_day=data.get('all_day', False),
                priority=data.get('priority', 'medium'),
                status=data.get('status', 'planned'),
                booking_required=data.get('booking_required', False),
                booking_url=data.get('booking_url'),
                booking_reference=data.get('booking_reference'),
                booking_status=data.get('booking_status'),
                cost=data.get('cost', 0.0),
                currency=data.get('currency', 'USD'),
                paid=data.get('paid', False),
                contact_phone=data.get('contact_phone'),
                contact_email=data.get('contact_email'),
                website=data.get('website'),
                notes=data.get('notes'),
                weather_dependent=data.get('weather_dependent', False),
                indoor=data.get('indoor', False),
                accessibility=data.get('accessibility'),
                age_restriction=data.get('age_restriction'),
                dress_code=data.get('dress_code'),
                tags=data.get('tags', []),
                created_by=data.get('user_id')
            )
            
            db.session.add(activity)
            db.session.commit()
            
            return activity.to_dict(), None, 201
        
        except ValueError as e:
            return None, {'error': f'Invalid data format: {str(e)}'}, 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating activity: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def update_activity(activity_id, data):
        """Update an activity"""
        try:
            activity = Activity.query.get(activity_id)
            if not activity:
                return None, {'error': 'Activity not found'}, 404
            
            # Update fields
            if 'title' in data:
                activity.title = data['title']
            if 'description' in data:
                activity.description = data['description']
            if 'category' in data:
                activity.category = data['category']
            if 'location' in data:
                activity.location = data['location']
            if 'address' in data:
                activity.address = data['address']
            if 'latitude' in data:
                activity.latitude = data['latitude']
            if 'longitude' in data:
                activity.longitude = data['longitude']
            if 'activity_date' in data:
                activity.activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
            if 'start_time' in data and data['start_time']:
                activity.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            if 'end_time' in data and data['end_time']:
                activity.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            if 'duration_minutes' in data:
                activity.duration_minutes = data['duration_minutes']
            if 'all_day' in data:
                activity.all_day = data['all_day']
            if 'priority' in data:
                activity.priority = data['priority']
            if 'status' in data:
                activity.status = data['status']
                if data['status'] == 'completed':
                    activity.completed_at = datetime.utcnow()
            if 'booking_required' in data:
                activity.booking_required = data['booking_required']
            if 'booking_url' in data:
                activity.booking_url = data['booking_url']
            if 'booking_reference' in data:
                activity.booking_reference = data['booking_reference']
            if 'booking_status' in data:
                activity.booking_status = data['booking_status']
            if 'cost' in data:
                activity.cost = data['cost']
            if 'currency' in data:
                activity.currency = data['currency']
            if 'paid' in data:
                activity.paid = data['paid']
            if 'contact_phone' in data:
                activity.contact_phone = data['contact_phone']
            if 'contact_email' in data:
                activity.contact_email = data['contact_email']
            if 'website' in data:
                activity.website = data['website']
            if 'rating' in data:
                if data['rating'] and (data['rating'] < 1 or data['rating'] > 5):
                    return None, {'error': 'Rating must be between 1 and 5'}, 400
                activity.rating = data['rating']
            if 'review' in data:
                activity.review = data['review']
            if 'photos' in data:
                activity.photos = data['photos']
            if 'notes' in data:
                activity.notes = data['notes']
            if 'weather_dependent' in data:
                activity.weather_dependent = data['weather_dependent']
            if 'indoor' in data:
                activity.indoor = data['indoor']
            if 'accessibility' in data:
                activity.accessibility = data['accessibility']
            if 'age_restriction' in data:
                activity.age_restriction = data['age_restriction']
            if 'dress_code' in data:
                activity.dress_code = data['dress_code']
            if 'tags' in data:
                activity.tags = data['tags']
            if 'day_plan_id' in data:
                activity.day_plan_id = data['day_plan_id']
            
            activity.updated_at = datetime.utcnow()
            db.session.commit()
            
            return activity.to_dict(), None, 200
        
        except ValueError as e:
            return None, {'error': f'Invalid data format: {str(e)}'}, 400
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating activity: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def delete_activity(activity_id):
        """Delete an activity"""
        try:
            activity = Activity.query.get(activity_id)
            if not activity:
                return None, {'error': 'Activity not found'}, 404
            
            db.session.delete(activity)
            db.session.commit()
            
            return {'message': 'Activity deleted successfully'}, None, 200
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting activity: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def get_activities_by_category(trip_id):
        """Get activities grouped by category"""
        try:
            activities = Activity.query.filter_by(trip_id=trip_id).all()
            
            categories = {}
            for activity in activities:
                category = activity.category or 'other'
                if category not in categories:
                    categories[category] = []
                categories[category].append(activity.to_dict())
            
            return categories, None, 200
        
        except Exception as e:
            logger.error(f"Error getting activities by category: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def get_activities_by_status(trip_id):
        """Get activities grouped by status"""
        try:
            activities = Activity.query.filter_by(trip_id=trip_id).all()
            
            statuses = {}
            for activity in activities:
                status = activity.status or 'planned'
                if status not in statuses:
                    statuses[status] = []
                statuses[status].append(activity.to_dict())
            
            return statuses, None, 200
        
        except Exception as e:
            logger.error(f"Error getting activities by status: {str(e)}")
            return None, {'error': str(e)}, 500
    
    @staticmethod
    def _calculate_itinerary_stats(trip_id):
        """Calculate statistics for itinerary"""
        try:
            from sqlalchemy import func
            
            activities = Activity.query.filter_by(trip_id=trip_id).all()
            
            total_activities = len(activities)
            total_cost = sum(a.cost for a in activities if a.cost)
            
            status_counts = db.session.query(
                Activity.status,
                func.count(Activity.id)
            ).filter_by(trip_id=trip_id).group_by(Activity.status).all()
            
            category_counts = db.session.query(
                Activity.category,
                func.count(Activity.id)
            ).filter_by(trip_id=trip_id).group_by(Activity.category).all()
            
            priority_counts = db.session.query(
                Activity.priority,
                func.count(Activity.id)
            ).filter_by(trip_id=trip_id).group_by(Activity.priority).all()
            
            booking_required = Activity.query.filter_by(
                trip_id=trip_id,
                booking_required=True
            ).count()
            
            booked = Activity.query.filter_by(
                trip_id=trip_id,
                booking_status='confirmed'
            ).count()
            
            return {
                'total_activities': total_activities,
                'total_cost': total_cost,
                'by_status': dict(status_counts),
                'by_category': dict(category_counts),
                'by_priority': dict(priority_counts),
                'booking_required': booking_required,
                'booked': booked,
                'booking_progress': round((booked / booking_required * 100), 2) if booking_required > 0 else 100
            }
        
        except Exception as e:
            logger.error(f"Error calculating stats: {str(e)}")
            return {}
    
    @staticmethod
    def auto_generate_day_plans(trip_id):
        """Auto-generate day plans for entire trip"""
        try:
            trip = Trip.query.get(trip_id)
            if not trip:
                return None, {'error': 'Trip not found'}, 404
            
            current_date = trip.start_date
            day_plans = []
            
            while current_date <= trip.end_date:
                day_number = (current_date - trip.start_date).days + 1
                
                # Check if day plan already exists
                existing = DayPlan.query.filter_by(trip_id=trip_id, date=current_date).first()
                
                if not existing:
                    day_plan = DayPlan(
                        trip_id=trip_id,
                        date=current_date,
                        day_number=day_number,
                        title=f'Day {day_number} - {trip.destination}'
                    )
                    db.session.add(day_plan)
                    day_plans.append(day_plan)
                
                current_date += timedelta(days=1)
            
            db.session.commit()
            
            return {
                'message': f'Generated {len(day_plans)} day plans',
                'day_plans': [dp.to_dict() for dp in day_plans]
            }, None, 201
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error auto-generating day plans: {str(e)}")
            return None, {'error': str(e)}, 500
