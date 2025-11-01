from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import db

trips_bp = Blueprint('trips', __name__)

@trips_bp.route('/', methods=['GET'])
@jwt_required()
def get_trips():
    """
    Get all trips for current user (owned and collaborated)
    ---
    tags:
      - Trips
    security:
      - Bearer: []
    responses:
      200:
        description: List of trips
        schema:
          type: object
          properties:
            trips:
              type: array
              items:
                type: object
    """
    from models import Trip, TripCollaborator
    
    current_user_id = int(get_jwt_identity())
    
    # Get trips owned by user
    owned_trips = Trip.query.filter_by(user_id=current_user_id).all()
    
    # Get trips where user is a collaborator
    collaborations = TripCollaborator.query.filter_by(
        user_id=current_user_id,
        status='accepted'
    ).all()
    
    collaborated_trip_ids = [c.trip_id for c in collaborations]
    collaborated_trips = Trip.query.filter(Trip.id.in_(collaborated_trip_ids)).all() if collaborated_trip_ids else []
    
    # Combine and format trips
    all_trips = []
    
    for trip in owned_trips:
        trip_dict = trip.to_dict()
        trip_dict['is_owner'] = True
        trip_dict['role'] = 'owner'
        all_trips.append(trip_dict)
    
    for trip in collaborated_trips:
        collab = next((c for c in collaborations if c.trip_id == trip.id), None)
        trip_dict = trip.to_dict()
        trip_dict['is_owner'] = False
        trip_dict['role'] = collab.role.value if collab else 'viewer'
        all_trips.append(trip_dict)
    
    return jsonify({
        'trips': all_trips,
        'owned_count': len(owned_trips),
        'collaborated_count': len(collaborated_trips)
    }), 200

@trips_bp.route('/<int:trip_id>', methods=['GET'])
@jwt_required()
def get_trip(trip_id):
    """
    Get a specific trip
    ---
    tags:
      - Trips
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Trip details
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    # Check if user has access (owner or collaborator)
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized to view this trip'}), 403
    
    trip_dict = trip.to_dict()
    trip_dict['is_owner'] = trip.user_id == current_user_id
    
    return jsonify(trip_dict), 200

@trips_bp.route('/', methods=['POST'])
@jwt_required()
def create_trip():
    """
    Create a new trip
    ---
    tags:
      - Trips
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - title
            - destination
            - start_date
            - end_date
          properties:
            title:
              type: string
              example: Summer Vacation
            destination:
              type: string
              example: Paris, France
            start_date:
              type: string
              format: date
              example: "2024-07-01"
            end_date:
              type: string
              format: date
              example: "2024-07-15"
            description:
              type: string
              example: A wonderful trip to Paris
            budget:
              type: number
              example: 5000.0
            status:
              type: string
              example: planned
    responses:
      201:
        description: Trip created successfully
      400:
        description: Invalid input
    """
    from models import Trip
    
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    required_fields = ['title', 'destination', 'start_date', 'end_date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        if end_date < start_date:
            return jsonify({'error': 'End date must be after start date'}), 400
        
        trip = Trip(
            title=data['title'],
            destination=data['destination'],
            start_date=start_date,
            end_date=end_date,
            description=data.get('description'),
            budget=data.get('budget'),
            status=data.get('status', 'planned'),
            user_id=current_user_id
        )
        
        db.session.add(trip)
        db.session.commit()
        
        return jsonify({
            'message': 'Trip created successfully',
            'trip': trip.to_dict()
        }), 201
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

@trips_bp.route('/<int:trip_id>', methods=['PUT'])
@jwt_required()
def update_trip(trip_id):
    """
    Update a trip
    ---
    tags:
      - Trips
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            title:
              type: string
            destination:
              type: string
            start_date:
              type: string
              format: date
            end_date:
              type: string
              format: date
            description:
              type: string
            budget:
              type: number
            status:
              type: string
    responses:
      200:
        description: Trip updated successfully
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    # Check if user has edit permission
    if not CollaboratorService.can_edit_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized to edit this trip. Editor role required.'}), 403
    
    data = request.get_json()
    
    try:
        if 'title' in data:
            trip.title = data['title']
        if 'destination' in data:
            trip.destination = data['destination']
        if 'start_date' in data:
            trip.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data:
            trip.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        if 'description' in data:
            trip.description = data['description']
        if 'budget' in data:
            trip.budget = data['budget']
        if 'status' in data:
            trip.status = data['status']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Trip updated successfully',
            'trip': trip.to_dict()
        }), 200
    
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

@trips_bp.route('/<int:trip_id>', methods=['DELETE'])
@jwt_required()
def delete_trip(trip_id):
    """
    Delete a trip
    ---
    tags:
      - Trips
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
    responses:
      200:
        description: Trip deleted successfully
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    # Only trip owner can delete the trip
    if not CollaboratorService.is_trip_owner(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized. Only trip owner can delete the trip.'}), 403
    
    db.session.delete(trip)
    db.session.commit()
    
    return jsonify({'message': 'Trip deleted successfully'}), 200


# ============= Weather Endpoints =============

@trips_bp.route('/<int:trip_id>/weather', methods=['GET'])
@jwt_required()
def get_trip_weather(trip_id):
    """
    Get comprehensive weather information for trip
    ---
    tags:
      - Trips
      - Weather
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: Trip ID
    responses:
      200:
        description: Weather information for entire trip duration
        schema:
          type: object
          properties:
            destination:
              type: string
            current_weather:
              type: object
            forecast:
              type: array
            recommendations:
              type: object
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    from utils.weather_service import WeatherService
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized to view this trip'}), 403
    
    # Get comprehensive weather data
    weather_data = WeatherService.get_trip_weather(
        trip.destination,
        trip.start_date,
        trip.end_date
    )
    
    return jsonify(weather_data), 200


@trips_bp.route('/<int:trip_id>/weather/current', methods=['GET'])
@jwt_required()
def get_current_weather(trip_id):
    """
    Get current weather for trip destination
    ---
    tags:
      - Trips
      - Weather
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: Trip ID
    responses:
      200:
        description: Current weather data
        schema:
          type: object
          properties:
            destination:
              type: string
            trip_id:
              type: integer
            weather:
              type: object
      400:
        description: Unable to fetch weather data
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    from utils.weather_service import WeatherService
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    result = WeatherService.get_current_weather(trip.destination)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'destination': trip.destination,
        'trip_id': trip_id,
        'trip_dates': {
            'start': trip.start_date.isoformat(),
            'end': trip.end_date.isoformat()
        },
        'weather': result['data']
    }), 200


@trips_bp.route('/<int:trip_id>/weather/forecast', methods=['GET'])
@jwt_required()
def get_weather_forecast(trip_id):
    """
    Get weather forecast for trip destination
    ---
    tags:
      - Trips
      - Weather
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: Trip ID
      - in: query
        name: days
        type: integer
        default: 5
        description: Number of days for forecast (max 5)
    responses:
      200:
        description: Weather forecast
        schema:
          type: object
          properties:
            destination:
              type: string
            trip_id:
              type: integer
            forecast:
              type: object
      400:
        description: Unable to fetch forecast data
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    from utils.weather_service import WeatherService
    
    current_user_id = int(get_jwt_identity())
    days = int(request.args.get('days', 5))
    
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    result = WeatherService.get_forecast(trip.destination, min(days, 5))
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'destination': trip.destination,
        'trip_id': trip_id,
        'trip_dates': {
            'start': trip.start_date.isoformat(),
            'end': trip.end_date.isoformat()
        },
        'forecast': result['data']
    }), 200


@trips_bp.route('/<int:trip_id>/weather/recommendations', methods=['GET'])
@jwt_required()
def get_weather_recommendations(trip_id):
    """
    Get packing and activity recommendations based on weather
    ---
    tags:
      - Trips
      - Weather
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: Trip ID
    responses:
      200:
        description: Weather-based recommendations for packing and activities
        schema:
          type: object
          properties:
            trip_id:
              type: integer
            destination:
              type: string
            trip_dates:
              type: object
            recommendations:
              type: object
              properties:
                clothing:
                  type: array
                  items:
                    type: string
                activities:
                  type: array
                  items:
                    type: string
                precautions:
                  type: array
                  items:
                    type: string
      400:
        description: Unable to fetch weather data
      403:
        description: Unauthorized
      404:
        description: Trip not found
    """
    from models import Trip
    from utils.collaborator_service import CollaboratorService
    from utils.weather_service import WeatherService
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.get(trip_id)
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get current weather
    weather_result = WeatherService.get_current_weather(trip.destination)
    
    if not weather_result['success']:
        return jsonify({'error': weather_result['error']}), 400
    
    recommendations = WeatherService._generate_recommendations(weather_result['data'])
    
    return jsonify({
        'trip_id': trip_id,
        'destination': trip.destination,
        'trip_dates': {
            'start': trip.start_date.isoformat(),
            'end': trip.end_date.isoformat()
        },
        'current_weather': {
            'temperature': weather_result['data']['temperature'],
            'conditions': weather_result['data']['conditions']
        },
        'recommendations': recommendations
    }), 200
