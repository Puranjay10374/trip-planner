from flask import jsonify

class ResponseFormatter:
    """Utility class for consistent API responses"""
    
    @staticmethod
    def success(data, message='Success', status_code=200):
        """Format successful response"""
        return jsonify({
            'success': True,
            'message': message,
            'data': data
        }), status_code
    
    @staticmethod
    def created(data, message='Resource created successfully'):
        """Format resource creation response"""
        return jsonify({
            'success': True,
            'message': message,
            'data': data
        }), 201
    
    @staticmethod
    def error(message, status_code=400):
        """Format error response"""
        return jsonify({
            'success': False,
            'error': message
        }), status_code
    
    @staticmethod
    def unauthorized(message='Unauthorized access'):
        """Format unauthorized response"""
        return jsonify({
            'success': False,
            'error': message
        }), 403
    
    @staticmethod
    def not_found(message='Resource not found'):
        """Format not found response"""
        return jsonify({
            'success': False,
            'error': message
        }), 404
    
    @staticmethod
    def handle_service_response(result, error, status_code):
        """Handle service layer response"""
        if error:
            return ResponseFormatter.error(error.get('error', 'An error occurred'), status_code)
        
        if status_code == 201:
            return ResponseFormatter.created(result)
        
        return ResponseFormatter.success(result, status_code=status_code)
