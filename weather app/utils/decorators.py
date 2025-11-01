from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from utils.collaborator_service import CollaboratorService

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid or expired token'}), 401
    return decorated_function


def collaborator_required(permission='view'):
    """
    Decorator to check if user has permission to access trip
    Usage:
        @collaborator_required('view')  - viewer, editor, or owner
        @collaborator_required('edit')  - editor or owner
        @collaborator_required('owner') - owner only
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                current_user_id = int(get_jwt_identity())
                
                # Get trip_id from URL parameters
                trip_id = kwargs.get('trip_id')
                if not trip_id:
                    return jsonify({'error': 'Trip ID required'}), 400
                
                # Check permission based on level
                if permission == 'owner':
                    if not CollaboratorService.is_trip_owner(trip_id, current_user_id):
                        return jsonify({'error': 'Only trip owner can perform this action'}), 403
                elif permission == 'edit':
                    if not CollaboratorService.can_edit_trip(trip_id, current_user_id):
                        return jsonify({'error': 'Editor or owner permission required'}), 403
                else:  # view
                    if not CollaboratorService.can_view_trip(trip_id, current_user_id):
                        return jsonify({'error': 'You do not have permission to view this trip'}), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': str(e)}), 401
        return decorated_function
    return decorator
