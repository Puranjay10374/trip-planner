"""Blueprint for trip collaborator management"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flasgger import swag_from

collaborators_bp = Blueprint('collaborators', __name__)


@collaborators_bp.route('/trips/<int:trip_id>/collaborators', methods=['POST'])
@jwt_required()
def add_collaborator(trip_id):
    """
    Add a collaborator to a trip
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: ID of the trip
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - user_id
          properties:
            user_id:
              type: integer
              description: ID of the user to add as collaborator
              example: 2
            role:
              type: string
              enum: [viewer, editor, owner]
              default: viewer
              description: Role of the collaborator
              example: editor
    responses:
      201:
        description: Collaborator invited successfully
        schema:
          type: object
          properties:
            message:
              type: string
            collaborator:
              type: object
      400:
        description: Bad request (user already collaborator, limit reached, etc.)
      403:
        description: Unauthorized (only owner/editors can invite)
      404:
        description: User or trip not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or 'user_id' not in data:
        return jsonify({'error': 'user_id is required'}), 400
    
    result, status = CollaboratorService.add_collaborator(
        trip_id=trip_id,
        user_id=data['user_id'],
        invited_by_id=current_user_id,
        role=data.get('role', 'viewer')
    )
    
    return jsonify(result), status


@collaborators_bp.route('/trips/<int:trip_id>/collaborators', methods=['GET'])
@jwt_required()
def get_collaborators(trip_id):
    """
    Get all collaborators for a trip
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: ID of the trip
    responses:
      200:
        description: List of collaborators
        schema:
          type: object
          properties:
            collaborators:
              type: array
              items:
                type: object
            count:
              type: integer
      403:
        description: Unauthorized to view collaborators
      404:
        description: Trip not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    result, status = CollaboratorService.get_trip_collaborators(trip_id, current_user_id)
    
    return jsonify(result), status


@collaborators_bp.route('/collaborators/<int:collaborator_id>/accept', methods=['POST'])
@jwt_required()
def accept_invitation(collaborator_id):
    """
    Accept a collaboration invitation
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: collaborator_id
        type: integer
        required: true
        description: ID of the collaborator invitation
    responses:
      200:
        description: Invitation accepted successfully
        schema:
          type: object
          properties:
            message:
              type: string
            collaborator:
              type: object
      400:
        description: Invitation already processed or expired
      403:
        description: Unauthorized to accept this invitation
      404:
        description: Invitation not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    result, status = CollaboratorService.accept_invitation(collaborator_id, current_user_id)
    
    return jsonify(result), status


@collaborators_bp.route('/collaborators/<int:collaborator_id>/reject', methods=['POST'])
@jwt_required()
def reject_invitation(collaborator_id):
    """
    Reject a collaboration invitation
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: collaborator_id
        type: integer
        required: true
        description: ID of the collaborator invitation
    responses:
      200:
        description: Invitation rejected successfully
        schema:
          type: object
          properties:
            message:
              type: string
      400:
        description: Invitation already processed
      403:
        description: Unauthorized to reject this invitation
      404:
        description: Invitation not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    result, status = CollaboratorService.reject_invitation(collaborator_id, current_user_id)
    
    return jsonify(result), status


@collaborators_bp.route('/trips/<int:trip_id>/collaborators/<int:collaborator_id>', methods=['DELETE'])
@jwt_required()
def remove_collaborator(trip_id, collaborator_id):
    """
    Remove a collaborator from a trip
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: ID of the trip
      - in: path
        name: collaborator_id
        type: integer
        required: true
        description: ID of the collaborator to remove
    responses:
      200:
        description: Collaborator removed successfully
        schema:
          type: object
          properties:
            message:
              type: string
      403:
        description: Unauthorized to remove this collaborator
      404:
        description: Collaborator not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    result, status = CollaboratorService.remove_collaborator(
        trip_id, collaborator_id, current_user_id
    )
    
    return jsonify(result), status


@collaborators_bp.route('/trips/<int:trip_id>/collaborators/<int:collaborator_id>/role', methods=['PUT'])
@jwt_required()
def update_collaborator_role(trip_id, collaborator_id):
    """
    Update a collaborator's role
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: path
        name: trip_id
        type: integer
        required: true
        description: ID of the trip
      - in: path
        name: collaborator_id
        type: integer
        required: true
        description: ID of the collaborator
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - role
          properties:
            role:
              type: string
              enum: [viewer, editor, owner]
              description: New role for the collaborator
              example: editor
    responses:
      200:
        description: Role updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
            collaborator:
              type: object
      400:
        description: Invalid role or collaborator not accepted
      403:
        description: Only trip owner can update roles
      404:
        description: Collaborator or trip not found
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or 'role' not in data:
        return jsonify({'error': 'role is required'}), 400
    
    result, status = CollaboratorService.update_role(
        trip_id, collaborator_id, data['role'], current_user_id
    )
    
    return jsonify(result), status


@collaborators_bp.route('/invitations', methods=['GET'])
@jwt_required()
def get_my_invitations():
    """
    Get all invitations for the current user
    ---
    tags:
      - Collaborators
    security:
      - Bearer: []
    parameters:
      - in: query
        name: status
        type: string
        enum: [pending, accepted, rejected]
        description: Filter invitations by status
    responses:
      200:
        description: List of invitations
        schema:
          type: object
          properties:
            invitations:
              type: array
              items:
                type: object
            count:
              type: integer
    """
    from utils.collaborator_service import CollaboratorService
    
    current_user_id = int(get_jwt_identity())
    status_filter = request.args.get('status')
    
    result, status = CollaboratorService.get_user_invitations(
        current_user_id, status_filter
    )
    
    return jsonify(result), status
