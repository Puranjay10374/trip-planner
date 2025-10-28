from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db

users_bp = Blueprint('users', __name__)

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: User profile
        schema:
          type: object
          properties:
            id:
              type: integer
            username:
              type: string
            email:
              type: string
            created_at:
              type: string
      401:
        description: Unauthorized
    """
    from models import User
    
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@users_bp.route('/profile', methods=['DELETE'])
@jwt_required()
def delete_profile():
    """
    Delete current user account
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: Account deleted successfully
      401:
        description: Unauthorized
    """
    from models import User
    
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'Account deleted successfully'}), 200
