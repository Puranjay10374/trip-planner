"""
Chatbot Blueprint
Provides chatbot API endpoints for FAQ assistance
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils.chatbot_service import chatbot_service
from utils.response_formatter import ResponseFormatter

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/ask', methods=['POST'])
@jwt_required()
def ask_chatbot():
    """
    Ask a question to the chatbot
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - question
          properties:
            question:
              type: string
              description: The question to ask the chatbot
              example: "How do I split expenses with friends?"
            include_user_context:
              type: boolean
              description: Whether to include user context in the response
              default: true
    responses:
      200:
        description: Chatbot response
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            answer:
              type: string
              example: "When adding an expense: 1) Check 'Split this expense'. 2) Choose split type..."
            question:
              type: string
              example: "How do I split expenses with friends?"
            model:
              type: string
              example: "gpt-3.5-turbo"
            tokens_used:
              type: integer
              example: 150
      400:
        description: Invalid request
      401:
        description: Unauthorized
      503:
        description: Chatbot service unavailable
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return ResponseFormatter.error('Request body is required', 400)
        
        question = data.get('question')
        include_user_context = data.get('include_user_context', True)
        
        # Validate question
        if not question:
            return ResponseFormatter.error('Question is required', 400)
        
        if not isinstance(question, str):
            return ResponseFormatter.error('Question must be a string', 400)
        
        question = question.strip()
        if not question:
            return ResponseFormatter.error('Question cannot be empty', 400)
        
        if len(question) > 500:
            return ResponseFormatter.error('Question is too long (max 500 characters)', 400)
        
        # Check if chatbot service is available
        if not chatbot_service.is_available():
            return ResponseFormatter.error(
                'Chatbot service is currently unavailable. Please check API configuration.',
                503
            )
        
        # Prepare user context if requested
        user_context = None
        if include_user_context:
            try:
                current_user = get_jwt_identity()
                user_context = {
                    'username': current_user.get('username') if isinstance(current_user, dict) else current_user
                }
            except:
                # If we can't get user context, continue without it
                pass
        
        # Ask the chatbot
        result = chatbot_service.ask(question, user_context)
        
        # Handle result
        if not result.get('success'):
            return ResponseFormatter.error(
                result.get('error', 'Failed to get response from chatbot'),
                500
            )
        
        # Return successful response
        return ResponseFormatter.success(
            'Answer retrieved successfully',
            {
                'answer': result.get('answer'),
                'question': result.get('question'),
                'model': result.get('model'),
                'tokens_used': result.get('tokens_used')
            }
        )
        
    except Exception as e:
        return ResponseFormatter.error(f'Error processing chatbot request: {str(e)}', 500)


@chatbot_bp.route('/health', methods=['GET'])
def chatbot_health():
    """
    Check chatbot service health
    ---
    tags:
      - Chatbot
    responses:
      200:
        description: Chatbot service status
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            status:
              type: string
              example: "operational"
            faq_count:
              type: integer
              example: 44
            api_configured:
              type: boolean
              example: true
    """
    try:
        is_available = chatbot_service.is_available()
        faq_count = chatbot_service.get_faq_count()
        
        status = {
            'status': 'operational' if is_available else 'unavailable',
            'faq_count': faq_count,
            'api_configured': chatbot_service._client is not None,
            'faqs_loaded': faq_count > 0
        }
        
        return ResponseFormatter.success(
            'Chatbot service health check',
            status
        )
        
    except Exception as e:
        return ResponseFormatter.error(f'Error checking chatbot health: {str(e)}', 500)


@chatbot_bp.route('/search', methods=['POST'])
@jwt_required()
def search_faqs():
    """
    Search FAQs by keyword
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - query
          properties:
            query:
              type: string
              description: Search query
              example: "expense"
            limit:
              type: integer
              description: Maximum number of results
              default: 5
              example: 5
    responses:
      200:
        description: Search results
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            results:
              type: array
              items:
                type: object
                properties:
                  question:
                    type: string
                  answer:
                    type: string
            count:
              type: integer
              example: 3
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return ResponseFormatter.error('Request body is required', 400)
        
        query = data.get('query')
        limit = data.get('limit', 5)
        
        # Validate query
        if not query:
            return ResponseFormatter.error('Search query is required', 400)
        
        if not isinstance(query, str):
            return ResponseFormatter.error('Query must be a string', 400)
        
        query = query.strip()
        if not query:
            return ResponseFormatter.error('Query cannot be empty', 400)
        
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 50:
            limit = 5
        
        # Search FAQs
        results = chatbot_service.search_faqs(query, limit)
        
        return ResponseFormatter.success(
            f'Found {len(results)} matching FAQs',
            {
                'results': results,
                'count': len(results),
                'query': query
            }
        )
        
    except Exception as e:
        return ResponseFormatter.error(f'Error searching FAQs: {str(e)}', 500)


@chatbot_bp.route('/faqs', methods=['GET'])
@jwt_required()
def get_all_faqs():
    """
    Get all available FAQs
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    responses:
      200:
        description: List of all FAQs
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            faqs:
              type: array
              items:
                type: object
                properties:
                  question:
                    type: string
                  answer:
                    type: string
            count:
              type: integer
              example: 44
      401:
        description: Unauthorized
    """
    try:
        faqs = chatbot_service.get_all_faqs()
        
        return ResponseFormatter.success(
            f'Retrieved {len(faqs)} FAQs',
            {
                'faqs': faqs,
                'count': len(faqs)
            }
        )
        
    except Exception as e:
        return ResponseFormatter.error(f'Error retrieving FAQs: {str(e)}', 500)


@chatbot_bp.route('/reload', methods=['POST'])
@jwt_required()
def reload_faqs():
    """
    Reload FAQs from file (admin only)
    ---
    tags:
      - Chatbot
    security:
      - Bearer: []
    responses:
      200:
        description: FAQs reloaded successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "FAQs reloaded successfully"
            faq_count:
              type: integer
              example: 44
      401:
        description: Unauthorized
    """
    try:
        # Reload FAQs
        chatbot_service.reload_faqs()
        faq_count = chatbot_service.get_faq_count()
        
        return ResponseFormatter.success(
            'FAQs reloaded successfully',
            {
                'faq_count': faq_count
            }
        )
        
    except Exception as e:
        return ResponseFormatter.error(f'Error reloading FAQs: {str(e)}', 500)
