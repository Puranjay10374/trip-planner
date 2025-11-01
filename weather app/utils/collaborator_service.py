"""Service layer for collaborator management"""
from datetime import datetime, timedelta
from flask import current_app
from extensions import db
from models import TripCollaborator, CollaboratorRole, Trip, User


class CollaboratorService:
    """Service class for managing trip collaborators"""
    
    @staticmethod
    def add_collaborator(trip_id, user_id, invited_by_id, role='viewer'):
        """
        Add a collaborator to a trip
        
        Args:
            trip_id: ID of the trip
            user_id: ID of the user to be added as collaborator
            invited_by_id: ID of the user sending the invitation
            role: Role of the collaborator (viewer, editor, owner)
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return {'error': 'User not found'}, 404
        
        # Check if trip exists
        trip = Trip.query.get(trip_id)
        if not trip:
            return {'error': 'Trip not found'}, 404
        
        # Check if inviter has permission (must be owner or editor)
        inviter_permission = CollaboratorService.check_permission(
            trip_id, invited_by_id, 'editor'
        )
        
        # Also check if inviter is the trip owner
        is_trip_owner = trip.user_id == invited_by_id
        
        if not inviter_permission and not is_trip_owner:
            return {'error': 'Only trip owner or editors can invite collaborators'}, 403
        
        # Check if user is already the trip owner
        if trip.user_id == user_id:
            return {'error': 'User is already the trip owner'}, 400
        
        # Check if collaborator already exists
        existing = TripCollaborator.query.filter_by(
            trip_id=trip_id, 
            user_id=user_id
        ).first()
        
        if existing:
            if existing.status == 'pending':
                return {'error': 'User already has a pending invitation'}, 400
            elif existing.status == 'accepted':
                return {'error': 'User is already a collaborator'}, 400
            elif existing.status == 'rejected':
                # Allow re-invitation if previously rejected
                existing.status = 'pending'
                existing.invited_at = datetime.utcnow()
                existing.invited_by = invited_by_id
                existing.role = CollaboratorRole[role.upper()]
                db.session.commit()
                return {
                    'message': 'Collaborator re-invited successfully',
                    'collaborator': existing.to_dict()
                }, 201
        
        # Check max collaborators limit
        count = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            status='accepted'
        ).count()
        
        if count >= current_app.config['MAX_COLLABORATORS_PER_TRIP']:
            return {'error': 'Maximum collaborators limit reached'}, 400
        
        # Create new collaborator
        try:
            collaborator = TripCollaborator(
                trip_id=trip_id,
                user_id=user_id,
                role=CollaboratorRole[role.upper()],
                invited_by=invited_by_id,
                status='pending'
            )
            
            db.session.add(collaborator)
            db.session.commit()
            
            return {
                'message': 'Collaborator invited successfully',
                'collaborator': collaborator.to_dict()
            }, 201
        except KeyError:
            return {'error': 'Invalid role. Must be viewer, editor, or owner'}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to add collaborator: {str(e)}'}, 500
    
    @staticmethod
    def accept_invitation(collaborator_id, user_id):
        """
        Accept collaboration invitation
        
        Args:
            collaborator_id: ID of the collaborator record
            user_id: ID of the user accepting the invitation
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        collaborator = TripCollaborator.query.get(collaborator_id)
        
        if not collaborator:
            return {'error': 'Invitation not found'}, 404
        
        if collaborator.user_id != user_id:
            return {'error': 'Unauthorized to accept this invitation'}, 403
        
        if collaborator.status != 'pending':
            return {'error': f'Invitation already {collaborator.status}'}, 400
        
        # Check if invitation is expired
        expiry_days = current_app.config['COLLABORATION_INVITE_EXPIRY_DAYS']
        expiry_date = collaborator.invited_at + timedelta(days=expiry_days)
        
        if datetime.utcnow() > expiry_date:
            collaborator.status = 'expired'
            db.session.commit()
            return {'error': 'Invitation has expired'}, 400
        
        collaborator.status = 'accepted'
        collaborator.accepted_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'message': 'Invitation accepted successfully',
            'collaborator': collaborator.to_dict()
        }, 200
    
    @staticmethod
    def reject_invitation(collaborator_id, user_id):
        """
        Reject collaboration invitation
        
        Args:
            collaborator_id: ID of the collaborator record
            user_id: ID of the user rejecting the invitation
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        collaborator = TripCollaborator.query.get(collaborator_id)
        
        if not collaborator:
            return {'error': 'Invitation not found'}, 404
        
        if collaborator.user_id != user_id:
            return {'error': 'Unauthorized to reject this invitation'}, 403
        
        if collaborator.status != 'pending':
            return {'error': f'Invitation already {collaborator.status}'}, 400
        
        collaborator.status = 'rejected'
        db.session.commit()
        
        return {'message': 'Invitation rejected successfully'}, 200
    
    @staticmethod
    def remove_collaborator(trip_id, collaborator_id, requester_id):
        """
        Remove a collaborator from a trip
        
        Args:
            trip_id: ID of the trip
            collaborator_id: ID of the collaborator to remove
            requester_id: ID of the user making the request
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        collaborator = TripCollaborator.query.filter_by(
            id=collaborator_id,
            trip_id=trip_id
        ).first()
        
        if not collaborator:
            return {'error': 'Collaborator not found'}, 404
        
        trip = Trip.query.get(trip_id)
        if not trip:
            return {'error': 'Trip not found'}, 404
        
        # Check if requester has permission
        # Trip owner can remove anyone
        is_trip_owner = trip.user_id == requester_id
        
        # Check if requester is an owner role collaborator
        requester_collab = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            user_id=requester_id,
            status='accepted'
        ).first()
        
        is_owner_collaborator = requester_collab and requester_collab.role == CollaboratorRole.OWNER
        
        # Collaborator can remove themselves
        is_self_removal = collaborator.user_id == requester_id
        
        if not (is_trip_owner or is_owner_collaborator or is_self_removal):
            return {'error': 'Unauthorized to remove this collaborator'}, 403
        
        db.session.delete(collaborator)
        db.session.commit()
        
        return {'message': 'Collaborator removed successfully'}, 200
    
    @staticmethod
    def update_role(trip_id, collaborator_id, new_role, requester_id):
        """
        Update collaborator role
        
        Args:
            trip_id: ID of the trip
            collaborator_id: ID of the collaborator to update
            new_role: New role for the collaborator
            requester_id: ID of the user making the request
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        trip = Trip.query.get(trip_id)
        if not trip:
            return {'error': 'Trip not found'}, 404
        
        # Check if requester is trip owner or owner role collaborator
        is_trip_owner = trip.user_id == requester_id
        
        requester_collab = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            user_id=requester_id,
            status='accepted'
        ).first()
        
        is_owner_collaborator = requester_collab and requester_collab.role == CollaboratorRole.OWNER
        
        if not (is_trip_owner or is_owner_collaborator):
            return {'error': 'Only trip owner or owner-role collaborators can update roles'}, 403
        
        collaborator = TripCollaborator.query.get(collaborator_id)
        if not collaborator or collaborator.trip_id != trip_id:
            return {'error': 'Collaborator not found'}, 404
        
        if collaborator.status != 'accepted':
            return {'error': 'Can only update role for accepted collaborators'}, 400
        
        try:
            collaborator.role = CollaboratorRole[new_role.upper()]
            db.session.commit()
            
            return {
                'message': 'Role updated successfully',
                'collaborator': collaborator.to_dict()
            }, 200
        except KeyError:
            return {'error': 'Invalid role. Must be viewer, editor, or owner'}, 400
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update role: {str(e)}'}, 500
    
    @staticmethod
    def get_trip_collaborators(trip_id, requester_id):
        """
        Get all collaborators for a trip
        
        Args:
            trip_id: ID of the trip
            requester_id: ID of the user making the request
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        trip = Trip.query.get(trip_id)
        if not trip:
            return {'error': 'Trip not found'}, 404
        
        # Check if requester has access to this trip
        is_trip_owner = trip.user_id == requester_id
        is_collaborator = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            user_id=requester_id,
            status='accepted'
        ).first() is not None
        
        if not (is_trip_owner or is_collaborator):
            return {'error': 'Unauthorized to view collaborators'}, 403
        
        collaborators = TripCollaborator.query.filter_by(trip_id=trip_id).all()
        
        return {
            'collaborators': [c.to_dict() for c in collaborators],
            'count': len(collaborators)
        }, 200
    
    @staticmethod
    def get_user_invitations(user_id, status=None):
        """
        Get all invitations for a user
        
        Args:
            user_id: ID of the user
            status: Optional filter by status (pending, accepted, rejected)
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        query = TripCollaborator.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        invitations = query.all()
        
        return {
            'invitations': [inv.to_dict() for inv in invitations],
            'count': len(invitations)
        }, 200
    
    @staticmethod
    def check_permission(trip_id, user_id, required_role='viewer'):
        """
        Check if user has required permission for a trip
        
        Args:
            trip_id: ID of the trip
            user_id: ID of the user
            required_role: Minimum required role (viewer, editor, owner)
            
        Returns:
            Boolean indicating if user has permission
        """
        # Check if user is the trip owner
        trip = Trip.query.get(trip_id)
        if trip and trip.user_id == user_id:
            return True
        
        # Check if user is a collaborator with sufficient permissions
        collaborator = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            user_id=user_id,
            status='accepted'
        ).first()
        
        if not collaborator:
            return False
        
        role_hierarchy = {
            'viewer': 0,
            'editor': 1,
            'owner': 2
        }
        
        user_role_level = role_hierarchy.get(collaborator.role.value, -1)
        required_role_level = role_hierarchy.get(required_role.lower(), 0)
        
        return user_role_level >= required_role_level
    
    @staticmethod
    def can_view_trip(trip_id, user_id):
        """Check if user can view a trip"""
        return CollaboratorService.check_permission(trip_id, user_id, 'viewer')
    
    @staticmethod
    def can_edit_trip(trip_id, user_id):
        """Check if user can edit a trip"""
        return CollaboratorService.check_permission(trip_id, user_id, 'editor')
    
    @staticmethod
    def is_trip_owner(trip_id, user_id):
        """Check if user is the trip owner or has owner role"""
        trip = Trip.query.get(trip_id)
        if trip and trip.user_id == user_id:
            return True
        
        collaborator = TripCollaborator.query.filter_by(
            trip_id=trip_id,
            user_id=user_id,
            status='accepted',
            role=CollaboratorRole.OWNER
        ).first()
        
        return collaborator is not None
