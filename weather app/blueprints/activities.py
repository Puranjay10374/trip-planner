from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import db
from collections import defaultdict
from utils.activity_service import ActivityService
from utils.collaborator_service import CollaboratorService
from utils.response_formatter import ResponseFormatter

activities_bp = Blueprint('activities', __name__)

# Valid activity categories
VALID_CATEGORIES = [
    'sightseeing', 'dining', 'adventure', 'shopping', 
    'relaxation', 'transport', 'accommodation', 'other'
]

VALID_PRIORITIES = ['low', 'medium', 'high', 'must-do']

@activities_bp.route('/trips/<int:trip_id>/activities', methods=['GET'])
@jwt_required()
def get_activities(trip_id):
    """
    Get all activities for a trip
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: Trip ID
      - in: query
        name: date
        type: string
        format: date
        description: Filter by specific date (YYYY-MM-DD)
      - in: query
        name: category
        type: string
        description: Filter by category
      - in: query
        name: priority
        type: string
        description: Filter by priority
      - in: query
        name: is_booked
        type: boolean
        description: Filter by booking status
    responses:
      200:
        description: List of activities
        schema:
          type: object
          properties:
            activities:
              type: array
              items:
                type: object
            count:
              type: integer
            total_cost:
              type: number
      404:
        description: Trip not found
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Verify trip ownership
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    # Build query
    query = Activity.query.filter_by(trip_id=trip_id)
    
    # Apply filters
    date_filter = request.args.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(activity_date=filter_date)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    category = request.args.get('category')
    if category and category in VALID_CATEGORIES:
        query = query.filter_by(category=category)
    
    priority = request.args.get('priority')
    if priority and priority in VALID_PRIORITIES:
        query = query.filter_by(priority=priority)
    
    is_booked = request.args.get('is_booked')
    if is_booked is not None:
        is_booked_bool = is_booked.lower() == 'true'
        query = query.filter_by(is_booked=is_booked_bool)
    
    # Order by date and time
    query = query.order_by(Activity.activity_date, Activity.start_time)
    
    activities = query.all()
    
    # Calculate total cost
    total_cost = sum(activity.cost or 0 for activity in activities)
    
    return jsonify({
        'activities': [activity.to_dict() for activity in activities],
        'count': len(activities),
        'total_cost': total_cost
    }), 200

@activities_bp.route('/trips/<int:trip_id>/activities/<int:activity_id>', methods=['GET'])
@jwt_required()
def get_activity(trip_id, activity_id):
    """
    Get a specific activity
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: path
        name: activity_id
        type: integer
        required: true
    responses:
      200:
        description: Activity details
      404:
        description: Activity not found
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Verify trip ownership
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    activity = Activity.query.filter_by(id=activity_id, trip_id=trip_id).first()
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    return jsonify(activity.to_dict()), 200

@activities_bp.route('/trips/<int:trip_id>/activities', methods=['POST'])
@jwt_required()
def create_activity(trip_id):
    """
    Create a new activity for a trip
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - activity_date
          properties:
            title:
              type: string
              example: Visit Eiffel Tower
            description:
              type: string
              example: Visit the iconic Eiffel Tower and enjoy the view
            location:
              type: string
              example: Champ de Mars, Paris
            activity_date:
              type: string
              format: date
              example: "2024-07-05"
            start_time:
              type: string
              format: time
              example: "09:00"
            end_time:
              type: string
              format: time
              example: "12:00"
            cost:
              type: number
              example: 26.0
            category:
              type: string
              enum: [sightseeing, dining, adventure, shopping, relaxation, transport, accommodation, other]
              example: sightseeing
            booking_reference:
              type: string
              example: EIF-12345
            booking_url:
              type: string
              example: https://www.toureiffel.paris/en
            notes:
              type: string
              example: Book tickets online to skip the queue
            is_booked:
              type: boolean
              example: true
            priority:
              type: string
              enum: [low, medium, high, must-do]
              example: must-do
    responses:
      201:
        description: Activity created successfully
      400:
        description: Invalid input
      404:
        description: Trip not found
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Verify trip ownership
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('title') or not data.get('activity_date'):
        return jsonify({'error': 'Title and activity_date are required'}), 400
    
    try:
        # Parse date
        activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
        
        # Validate date is within trip dates
        if activity_date < trip.start_date or activity_date > trip.end_date:
            return jsonify({
                'error': f'Activity date must be between trip start ({trip.start_date}) and end ({trip.end_date}) dates'
            }), 400
        
        # Parse times if provided
        start_time = None
        end_time = None
        
        if data.get('start_time'):
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        
        if data.get('end_time'):
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        
        # Validate time order
        if start_time and end_time and end_time <= start_time:
            return jsonify({'error': 'End time must be after start time'}), 400
        
        # Validate category
        category = data.get('category')
        if category and category not in VALID_CATEGORIES:
            return jsonify({'error': f'Invalid category. Must be one of: {", ".join(VALID_CATEGORIES)}'}), 400
        
        # Validate priority
        priority = data.get('priority', 'medium')
        if priority not in VALID_PRIORITIES:
            return jsonify({'error': f'Invalid priority. Must be one of: {", ".join(VALID_PRIORITIES)}'}), 400
        
        # Create activity
        activity = Activity(
            trip_id=trip_id,
            title=data['title'],
            description=data.get('description'),
            location=data.get('location'),
            activity_date=activity_date,
            start_time=start_time,
            end_time=end_time,
            cost=data.get('cost', 0.0),
            category=category,
            booking_reference=data.get('booking_reference'),
            booking_url=data.get('booking_url'),
            notes=data.get('notes'),
            is_booked=data.get('is_booked', False),
            priority=priority
        )
        
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'message': 'Activity created successfully',
            'activity': activity.to_dict()
        }), 201
    
    except ValueError as e:
        return jsonify({'error': f'Invalid format: {str(e)}'}), 400

@activities_bp.route('/trips/<int:trip_id>/activities/<int:activity_id>', methods=['PUT'])
@jwt_required()
def update_activity(trip_id, activity_id):
    """
    Update an activity
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: path
        name: activity_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            title:
              type: string
            description:
              type: string
            location:
              type: string
            activity_date:
              type: string
              format: date
            start_time:
              type: string
              format: time
            end_time:
              type: string
              format: time
            cost:
              type: number
            category:
              type: string
            booking_reference:
              type: string
            booking_url:
              type: string
            notes:
              type: string
            is_booked:
              type: boolean
            priority:
              type: string
    responses:
      200:
        description: Activity updated successfully
      404:
        description: Activity not found
      400:
        description: Invalid input
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Verify trip ownership
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    activity = Activity.query.filter_by(id=activity_id, trip_id=trip_id).first()
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update fields
        if 'title' in data:
            activity.title = data['title']
        
        if 'description' in data:
            activity.description = data['description']
        
        if 'location' in data:
            activity.location = data['location']
        
        if 'activity_date' in data:
            new_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
            if new_date < trip.start_date or new_date > trip.end_date:
                return jsonify({'error': 'Activity date must be within trip dates'}), 400
            activity.activity_date = new_date
        
        if 'start_time' in data:
            activity.start_time = datetime.strptime(data['start_time'], '%H:%M').time() if data['start_time'] else None
        
        if 'end_time' in data:
            activity.end_time = datetime.strptime(data['end_time'], '%H:%M').time() if data['end_time'] else None
        
        if 'cost' in data:
            activity.cost = data['cost']
        
        if 'category' in data:
            if data['category'] not in VALID_CATEGORIES:
                return jsonify({'error': f'Invalid category. Must be one of: {", ".join(VALID_CATEGORIES)}'}), 400
            activity.category = data['category']
        
        if 'booking_reference' in data:
            activity.booking_reference = data['booking_reference']
        
        if 'booking_url' in data:
            activity.booking_url = data['booking_url']
        
        if 'notes' in data:
            activity.notes = data['notes']
        
        if 'is_booked' in data:
            activity.is_booked = data['is_booked']
        
        if 'priority' in data:
            if data['priority'] not in VALID_PRIORITIES:
                return jsonify({'error': f'Invalid priority. Must be one of: {", ".join(VALID_PRIORITIES)}'}), 400
            activity.priority = data['priority']
        
        activity.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Activity updated successfully',
            'activity': activity.to_dict()
        }), 200
    
    except ValueError as e:
        return jsonify({'error': f'Invalid format: {str(e)}'}), 400

@activities_bp.route('/trips/<int:trip_id>/activities/<int:activity_id>', methods=['DELETE'])
@jwt_required()
def delete_activity(trip_id, activity_id):
    """
    Delete an activity
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: path
        name: activity_id
        type: integer
        required: true
    responses:
      200:
        description: Activity deleted successfully
      404:
        description: Activity not found
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Verify trip ownership
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    activity = Activity.query.filter_by(id=activity_id, trip_id=trip_id).first()
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404
    
    db.session.delete(activity)
    db.session.commit()
    
    return jsonify({'message': 'Activity deleted successfully'}), 200

@activities_bp.route('/trips/<int:trip_id>/itinerary', methods=['GET'])
@jwt_required()
def get_itinerary(trip_id):
    """
    Get full itinerary organized by date
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Full trip itinerary organized by date
        schema:
          type: object
          properties:
            trip:
              type: object
            itinerary:
              type: object
              additionalProperties:
                type: array
            summary:
              type: object
      404:
        description: Trip not found
    """
    from models import Trip, Activity
    
    current_user_id = int(get_jwt_identity())
    
    # Get trip
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    # Get all activities
    activities = Activity.query.filter_by(trip_id=trip_id).order_by(
        Activity.activity_date, Activity.start_time
    ).all()
    
    # Organize by date
    itinerary = defaultdict(list)
    for activity in activities:
        date_key = activity.activity_date.isoformat()
        itinerary[date_key].append(activity.to_dict())
    
    # Calculate summary
    total_activities = len(activities)
    total_cost = sum(activity.cost or 0 for activity in activities)
    booked_count = sum(1 for activity in activities if activity.is_booked)
    
    category_breakdown = defaultdict(int)
    for activity in activities:
        if activity.category:
            category_breakdown[activity.category] += 1
    
    return jsonify({
        'trip': trip.to_dict(),
        'itinerary': dict(itinerary),
        'summary': {
            'total_activities': total_activities,
            'total_cost': total_cost,
            'booked_activities': booked_count,
            'unbooked_activities': total_activities - booked_count,
            'activities_by_category': dict(category_breakdown)
        }
    }), 200


# ==================== DAY PLANS ENDPOINTS ====================

@activities_bp.route('/trips/<int:trip_id>/day-plans', methods=['POST'])
@jwt_required()
def create_day_plan(trip_id):
    """
    Create a day plan for a trip
    ---
    tags:
      - Day Plans
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - date
          properties:
            date:
              type: string
              format: date
              example: "2024-07-15"
            title:
              type: string
              example: "Day 1 - Arrival in Paris"
            description:
              type: string
              example: "Arrive at hotel and explore nearby areas"
            accommodation_id:
              type: integer
            total_distance:
              type: number
              example: 25.5
            estimated_cost:
              type: number
              example: 150.0
            notes:
              type: string
            is_rest_day:
              type: boolean
              default: false
    responses:
      201:
        description: Day plan created successfully
      400:
        description: Invalid input
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    current_user_id = int(get_jwt_identity())
    
    if not CollaboratorService.can_edit_trip(trip_id, current_user_id):
        return ResponseFormatter.unauthorized('You need editor role to create day plans')
    
    data = request.get_json()
    data['user_id'] = current_user_id
    
    date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    
    result, error, status_code = ActivityService.create_day_plan(trip_id, date, data)
    
    if error:
        return ResponseFormatter.error(error.get('error'), status_code)
    
    return ResponseFormatter.created(result, 'Day plan created successfully')


@activities_bp.route('/trips/<int:trip_id>/day-plans/auto-generate', methods=['POST'])
@jwt_required()
def auto_generate_day_plans(trip_id):
    """
    Auto-generate day plans for entire trip
    ---
    tags:
      - Day Plans
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      201:
        description: Day plans generated successfully
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    current_user_id = int(get_jwt_identity())
    
    if not CollaboratorService.can_edit_trip(trip_id, current_user_id):
        return ResponseFormatter.unauthorized('You need editor role to generate day plans')
    
    result, error, status_code = ActivityService.auto_generate_day_plans(trip_id)
    
    if error:
        return ResponseFormatter.error(error.get('error'), status_code)
    
    return ResponseFormatter.created(result, result.get('message'))


@activities_bp.route('/trips/<int:trip_id>/itinerary/enhanced', methods=['GET'])
@jwt_required()
def get_enhanced_itinerary(trip_id):
    """
    Get complete enhanced itinerary with day plans and statistics
    ---
    tags:
      - Day Plans
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Complete enhanced itinerary with day plans
        schema:
          type: object
          properties:
            trip_id:
              type: integer
            trip_title:
              type: string
            destination:
              type: string
            start_date:
              type: string
              format: date
            end_date:
              type: string
              format: date
            duration_days:
              type: integer
            day_plans:
              type: array
            unassigned_activities:
              type: array
            statistics:
              type: object
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    current_user_id = int(get_jwt_identity())
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return ResponseFormatter.unauthorized('You do not have permission to view this trip')
    
    result, error, status_code = ActivityService.get_trip_itinerary(trip_id)
    return ResponseFormatter.handle_service_response(result, error, status_code)


@activities_bp.route('/trips/<int:trip_id>/activities/by-category', methods=['GET'])
@jwt_required()
def get_activities_by_category(trip_id):
    """
    Get activities grouped by category
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Activities grouped by category
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    current_user_id = int(get_jwt_identity())
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return ResponseFormatter.unauthorized()
    
    result, error, status_code = ActivityService.get_activities_by_category(trip_id)
    return ResponseFormatter.handle_service_response(result, error, status_code)


@activities_bp.route('/trips/<int:trip_id>/activities/by-status', methods=['GET'])
@jwt_required()
def get_activities_by_status(trip_id):
    """
    Get activities grouped by status
    ---
    tags:
      - Activities
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Activities grouped by status
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    current_user_id = int(get_jwt_identity())
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return ResponseFormatter.unauthorized()
    
    result, error, status_code = ActivityService.get_activities_by_status(trip_id)
    return ResponseFormatter.handle_service_response(result, error, status_code)
