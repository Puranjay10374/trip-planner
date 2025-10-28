from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from extensions import db

trips_bp = Blueprint('trips', __name__)

@trips_bp.route('/', methods=['GET'])
@jwt_required()
def get_trips():
    """
    Get all trips for current user
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
    from models import Trip
    
    current_user_id = int(get_jwt_identity())
    trips = Trip.query.filter_by(user_id=current_user_id).all()
    
    return jsonify({
        'trips': [trip.to_dict() for trip in trips]
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
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    return jsonify(trip.to_dict()), 200

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
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
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
    
    current_user_id = int(get_jwt_identity())
    trip = Trip.query.filter_by(id=trip_id, user_id=current_user_id).first()
    
    if not trip:
        return jsonify({'error': 'Trip not found'}), 404
    
    db.session.delete(trip)
    db.session.commit()
    
    return jsonify({'message': 'Trip deleted successfully'}), 200
