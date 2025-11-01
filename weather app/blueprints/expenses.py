"""
Expenses Blueprint
Handles all expense, budget, and settlement related endpoints
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flasgger import swag_from
from models import Expense, ExpenseSplit, BudgetCategory, Settlement, Trip
from utils.expense_service import ExpenseService
from utils.collaborator_service import CollaboratorService
from utils.response_formatter import ResponseFormatter
from utils.decorators import collaborator_required
from datetime import datetime

expenses_bp = Blueprint('expenses', __name__, url_prefix='/api/expenses')


# Helper functions to maintain consistency with existing code pattern
def success_response(message, data, status_code=200):
    """Wrapper for ResponseFormatter to match the function signature used in this file"""
    if status_code == 201:
        return ResponseFormatter.created(data, message)
    return ResponseFormatter.success(data, message, status_code)


def error_response(message, status_code=400):
    """Wrapper for ResponseFormatter.error"""
    return ResponseFormatter.error(message, status_code)


# ============================================================================
# EXPENSE ENDPOINTS
# ============================================================================

@expenses_bp.route('/trips/<int:trip_id>/expenses', methods=['POST'])
@jwt_required()
@collaborator_required(['owner', 'editor'])
def create_expense(trip_id):
    """
    Create a new expense for a trip
    ---
    tags:
      - Expenses
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
        description: ID of the trip
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - title
            - amount
          properties:
            title:
              type: string
              example: "Hotel Stay"
            description:
              type: string
              example: "3 nights at Grand Hotel"
            amount:
              type: number
              example: 450.00
            currency:
              type: string
              example: "USD"
            category_id:
              type: integer
              example: 1
            expense_date:
              type: string
              format: date-time
              example: "2024-01-15T10:30:00"
            payment_method:
              type: string
              example: "Credit Card"
            receipt_url:
              type: string
              example: "https://example.com/receipts/12345.pdf"
            vendor_name:
              type: string
              example: "Grand Hotel"
            location:
              type: string
              example: "Paris, France"
            is_split:
              type: boolean
              example: true
            split_type:
              type: string
              enum: [equal, percentage, custom]
              example: "equal"
            splits:
              type: array
              items:
                type: object
                properties:
                  user_id:
                    type: integer
                  amount:
                    type: number
                  percentage:
                    type: number
                  notes:
                    type: string
            notes:
              type: string
    responses:
      201:
        description: Expense created successfully
      400:
        description: Invalid input
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    if not data.get('title') or not data.get('amount'):
        return ResponseFormatter.error('Title and amount are required', 400)
    
    # Check if trip exists
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    # Parse expense_date if provided
    if data.get('expense_date'):
        try:
            data['expense_date'] = datetime.fromisoformat(data['expense_date'].replace('Z', '+00:00'))
        except ValueError:
            return ResponseFormatter.error('Invalid expense_date format', 400)
    
    try:
        expense = ExpenseService.create_expense(
            trip_id=trip_id,
            paid_by=current_user_id,
            title=data['title'],
            amount=float(data['amount']),
            description=data.get('description'),
            currency=data.get('currency', 'USD'),
            category_id=data.get('category_id'),
            expense_date=data.get('expense_date'),
            payment_method=data.get('payment_method'),
            receipt_url=data.get('receipt_url'),
            vendor_name=data.get('vendor_name'),
            location=data.get('location'),
            is_split=data.get('is_split', False),
            split_type=data.get('split_type', 'equal'),
            splits=data.get('splits', []),
            notes=data.get('notes')
        )
        
        return success_response(
            'Expense created successfully',
            {'expense': expense.to_dict()},
            201
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to create expense: {str(e)}', 500)


@expenses_bp.route('/trips/<int:trip_id>/expenses', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def get_trip_expenses(trip_id):
    """
    Get all expenses for a trip
    ---
    tags:
      - Expenses
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
      - name: category_id
        in: query
        type: integer
        description: Filter by category
      - name: paid_by
        in: query
        type: integer
        description: Filter by payer user ID
      - name: is_settled
        in: query
        type: boolean
        description: Filter by settlement status
      - name: start_date
        in: query
        type: string
        format: date
        description: Filter expenses from this date
      - name: end_date
        in: query
        type: string
        format: date
        description: Filter expenses until this date
    responses:
      200:
        description: List of expenses
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    # Check if trip exists
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    # Build filters
    filters = {}
    if request.args.get('category_id'):
        filters['category_id'] = int(request.args.get('category_id'))
    if request.args.get('paid_by'):
        filters['paid_by'] = int(request.args.get('paid_by'))
    if request.args.get('is_settled'):
        filters['is_settled'] = request.args.get('is_settled').lower() == 'true'
    if request.args.get('start_date'):
        try:
            filters['start_date'] = datetime.fromisoformat(request.args.get('start_date'))
        except ValueError:
            pass
    if request.args.get('end_date'):
        try:
            filters['end_date'] = datetime.fromisoformat(request.args.get('end_date'))
        except ValueError:
            pass
    
    expenses = ExpenseService.get_trip_expenses(trip_id, filters)
    
    return success_response(
        'Expenses retrieved successfully',
        {
            'expenses': [e.to_dict() for e in expenses],
            'count': len(expenses)
        }
    )


@expenses_bp.route('/expenses/<int:expense_id>', methods=['GET'])
@jwt_required()
def get_expense(expense_id):
    """
    Get details of a specific expense
    ---
    tags:
      - Expenses
    parameters:
      - name: expense_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Expense details
      404:
        description: Expense not found
    """
    expense = Expense.query.get(expense_id)
    if not expense:
        return ResponseFormatter.error('Expense not found', 404)
    
    # Check if user has access to this trip
    current_user_id = get_jwt_identity()
    if not CollaboratorService.check_access(expense.trip_id, current_user_id, 'viewer'):
        return ResponseFormatter.error('You do not have access to this trip', 403)
    
    return success_response(
        'Expense retrieved successfully',
        {'expense': expense.to_dict()}
    )


@expenses_bp.route('/expenses/<int:expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    """
    Update an expense
    ---
    tags:
      - Expenses
    parameters:
      - name: expense_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            title:
              type: string
            description:
              type: string
            amount:
              type: number
            category_id:
              type: integer
            payment_method:
              type: string
            receipt_url:
              type: string
            vendor_name:
              type: string
            location:
              type: string
            notes:
              type: string
    responses:
      200:
        description: Expense updated successfully
      403:
        description: Permission denied
      404:
        description: Expense not found
    """
    expense = Expense.query.get(expense_id)
    if not expense:
        return ResponseFormatter.error('Expense not found', 404)
    
    # Check if user has editor access
    current_user_id = get_jwt_identity()
    if not CollaboratorService.check_access(expense.trip_id, current_user_id, 'editor'):
        return ResponseFormatter.error('You do not have permission to edit this expense', 403)
    
    data = request.get_json()
    
    try:
        updated_expense = ExpenseService.update_expense(expense_id, **data)
        return success_response(
            'Expense updated successfully',
            {'expense': updated_expense.to_dict()}
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to update expense: {str(e)}', 500)


@expenses_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@jwt_required()
def delete_expense(expense_id):
    """
    Delete an expense
    ---
    tags:
      - Expenses
    parameters:
      - name: expense_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Expense deleted successfully
      403:
        description: Permission denied
      404:
        description: Expense not found
    """
    expense = Expense.query.get(expense_id)
    if not expense:
        return ResponseFormatter.error('Expense not found', 404)
    
    # Check if user has editor access
    current_user_id = get_jwt_identity()
    if not CollaboratorService.check_access(expense.trip_id, current_user_id, 'editor'):
        return ResponseFormatter.error('You do not have permission to delete this expense', 403)
    
    try:
        ExpenseService.delete_expense(expense_id)
        return success_response('Expense deleted successfully', {})
    except Exception as e:
        return ResponseFormatter.error(f'Failed to delete expense: {str(e)}', 500)


# ============================================================================
# BUDGET ENDPOINTS
# ============================================================================

@expenses_bp.route('/trips/<int:trip_id>/budget', methods=['POST'])
@jwt_required()
@collaborator_required(['owner', 'editor'])
def create_budget_category(trip_id):
    """
    Create a budget category for a trip
    ---
    tags:
      - Budget
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - category
            - allocated_amount
          properties:
            category:
              type: string
              example: "Accommodation"
            allocated_amount:
              type: number
              example: 2000.00
            currency:
              type: string
              example: "USD"
            notes:
              type: string
    responses:
      201:
        description: Budget category created
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    data = request.get_json()
    
    if not data.get('category') or not data.get('allocated_amount'):
        return ResponseFormatter.error('Category and allocated_amount are required', 400)
    
    try:
        budget = ExpenseService.create_budget_category(
            trip_id=trip_id,
            category=data['category'],
            allocated_amount=float(data['allocated_amount']),
            currency=data.get('currency', 'USD'),
            notes=data.get('notes')
        )
        
        return success_response(
            'Budget category created successfully',
            {'budget_category': budget.to_dict()},
            201
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to create budget category: {str(e)}', 500)


@expenses_bp.route('/trips/<int:trip_id>/budget', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def get_trip_budget(trip_id):
    """
    Get budget overview for a trip
    ---
    tags:
      - Budget
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Budget overview
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    budget_overview = ExpenseService.get_trip_budget(trip_id)
    
    return success_response(
        'Budget retrieved successfully',
        {'budget': budget_overview}
    )


@expenses_bp.route('/budget/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_budget_category(category_id):
    """
    Update a budget category
    ---
    tags:
      - Budget
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        schema:
          type: object
          properties:
            category:
              type: string
            allocated_amount:
              type: number
            notes:
              type: string
    responses:
      200:
        description: Budget category updated
      403:
        description: Permission denied
      404:
        description: Budget category not found
    """
    budget = BudgetCategory.query.get(category_id)
    if not budget:
        return ResponseFormatter.error('Budget category not found', 404)
    
    # Check if user has editor access
    current_user_id = get_jwt_identity()
    if not CollaboratorService.check_access(budget.trip_id, current_user_id, 'editor'):
        return ResponseFormatter.error('You do not have permission to edit this budget', 403)
    
    data = request.get_json()
    
    try:
        updated_budget = ExpenseService._update_budget_category(category_id, **data)
        return success_response(
            'Budget category updated successfully',
            {'budget_category': updated_budget.to_dict()}
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to update budget category: {str(e)}', 500)


# ============================================================================
# SPLIT & SETTLEMENT ENDPOINTS
# ============================================================================

@expenses_bp.route('/splits/<int:split_id>/settle', methods=['POST'])
@jwt_required()
def settle_expense_split(split_id):
    """
    Mark an expense split as paid
    ---
    tags:
      - Splits
    parameters:
      - name: split_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Split settled successfully
      403:
        description: Permission denied
      404:
        description: Split not found
    """
    split = ExpenseSplit.query.get(split_id)
    if not split:
        return ResponseFormatter.error('Expense split not found', 404)
    
    # Only the user who owes or trip owner/editor can settle
    current_user_id = get_jwt_identity()
    expense = split.expense
    
    if current_user_id != split.user_id and \
       not CollaboratorService.check_access(expense.trip_id, current_user_id, 'editor'):
        return ResponseFormatter.error('You do not have permission to settle this split', 403)
    
    try:
        updated_split = ExpenseService.settle_split(split_id)
        return success_response(
            'Split settled successfully',
            {'split': updated_split.to_dict()}
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to settle split: {str(e)}', 500)


@expenses_bp.route('/trips/<int:trip_id>/settlements/calculate', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def calculate_settlements(trip_id):
    """
    Calculate settlements for a trip (who owes whom)
    ---
    tags:
      - Settlements
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Settlement calculations
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    settlements = ExpenseService.calculate_settlements(trip_id)
    
    return success_response(
        'Settlements calculated successfully',
        {
            'settlements': settlements,
            'count': len(settlements)
        }
    )


@expenses_bp.route('/trips/<int:trip_id>/settlements', methods=['POST'])
@jwt_required()
@collaborator_required(['owner', 'editor'])
def create_settlement(trip_id):
    """
    Create a settlement record
    ---
    tags:
      - Settlements
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - from_user_id
            - to_user_id
            - amount
          properties:
            from_user_id:
              type: integer
            to_user_id:
              type: integer
            amount:
              type: number
            currency:
              type: string
            payment_method:
              type: string
            notes:
              type: string
    responses:
      201:
        description: Settlement created
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    data = request.get_json()
    
    if not all(k in data for k in ['from_user_id', 'to_user_id', 'amount']):
        return error_response('from_user_id, to_user_id, and amount are required', 400)
    
    try:
        settlement = ExpenseService.create_settlement(
            trip_id=trip_id,
            from_user_id=data['from_user_id'],
            to_user_id=data['to_user_id'],
            amount=float(data['amount']),
            currency=data.get('currency', 'USD'),
            payment_method=data.get('payment_method'),
            notes=data.get('notes')
        )
        
        return success_response(
            'Settlement created successfully',
            {'settlement': settlement.to_dict()},
            201
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to create settlement: {str(e)}', 500)


@expenses_bp.route('/settlements/<int:settlement_id>/settle', methods=['POST'])
@jwt_required()
def mark_settlement_paid(settlement_id):
    """
    Mark a settlement as paid
    ---
    tags:
      - Settlements
    parameters:
      - name: settlement_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Settlement marked as paid
      403:
        description: Permission denied
      404:
        description: Settlement not found
    """
    settlement = Settlement.query.get(settlement_id)
    if not settlement:
        return ResponseFormatter.error('Settlement not found', 404)
    
    # Only involved users or trip editor can mark as paid
    current_user_id = get_jwt_identity()
    if current_user_id not in [settlement.from_user_id, settlement.to_user_id] and \
       not CollaboratorService.check_access(settlement.trip_id, current_user_id, 'editor'):
        return ResponseFormatter.error('You do not have permission to settle this', 403)
    
    try:
        updated_settlement = ExpenseService.mark_settlement_paid(settlement_id)
        return success_response(
            'Settlement marked as paid',
            {'settlement': updated_settlement.to_dict()}
        )
    except Exception as e:
        return ResponseFormatter.error(f'Failed to mark settlement as paid: {str(e)}', 500)


@expenses_bp.route('/trips/<int:trip_id>/settlements', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def get_trip_settlements(trip_id):
    """
    Get all settlements for a trip
    ---
    tags:
      - Settlements
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
      - name: settled
        in: query
        type: boolean
        description: Filter by settlement status
    responses:
      200:
        description: List of settlements
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    settled = None
    if request.args.get('settled'):
        settled = request.args.get('settled').lower() == 'true'
    
    settlements = ExpenseService.get_trip_settlements(trip_id, settled)
    
    return success_response(
        'Settlements retrieved successfully',
        {
            'settlements': [s.to_dict() for s in settlements],
            'count': len(settlements)
        }
    )


# ============================================================================
# ANALYTICS & EXPORT ENDPOINTS
# ============================================================================

@expenses_bp.route('/trips/<int:trip_id>/expenses/analytics', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def get_expense_analytics(trip_id):
    """
    Get comprehensive expense analytics for a trip
    ---
    tags:
      - Analytics
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Expense analytics
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    analytics = ExpenseService.get_expense_analytics(trip_id)
    
    return success_response(
        'Analytics retrieved successfully',
        {'analytics': analytics}
    )


@expenses_bp.route('/trips/<int:trip_id>/expenses/summary', methods=['GET'])
@jwt_required()
@collaborator_required(['owner', 'editor', 'viewer'])
def get_trip_expense_summary(trip_id):
    """
    Get a combined summary of expenses, budget, and settlements
    ---
    tags:
      - Analytics
    parameters:
      - name: trip_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Comprehensive trip financial summary
      403:
        description: Permission denied
      404:
        description: Trip not found
    """
    trip = Trip.query.get(trip_id)
    if not trip:
        return ResponseFormatter.error('Trip not found', 404)
    
    # Get all financial data
    budget = ExpenseService.get_trip_budget(trip_id)
    analytics = ExpenseService.get_expense_analytics(trip_id)
    settlements_pending = ExpenseService.get_trip_settlements(trip_id, settled=False)
    settlements_complete = ExpenseService.get_trip_settlements(trip_id, settled=True)
    
    summary = {
        'trip_info': {
            'id': trip.id,
            'name': trip.name,
            'destination': trip.destination,
            'start_date': trip.start_date.isoformat() if trip.start_date else None,
            'end_date': trip.end_date.isoformat() if trip.end_date else None
        },
        'budget': budget,
        'analytics': analytics,
        'settlements': {
            'pending': [s.to_dict() for s in settlements_pending],
            'completed': [s.to_dict() for s in settlements_complete],
            'pending_count': len(settlements_pending),
            'completed_count': len(settlements_complete)
        }
    }
    
    return success_response(
        'Trip expense summary retrieved successfully',
        {'summary': summary}
    )
