"""
Expense Service Module
Provides business logic for budget and expense management
"""

from extensions import db
from models import Expense, ExpenseSplit, BudgetCategory, Settlement, Trip, TripCollaborator, User
from datetime import datetime
from sqlalchemy import func


class ExpenseService:
    """Service class for handling expense operations"""
    
    @staticmethod
    def create_expense(trip_id, paid_by, title, amount, **kwargs):
        """
        Create a new expense for a trip
        
        Args:
            trip_id: ID of the trip
            paid_by: ID of user who paid
            title: Expense title
            amount: Expense amount
            **kwargs: Additional expense fields
            
        Returns:
            Created expense object
        """
        expense = Expense(
            trip_id=trip_id,
            paid_by=paid_by,
            title=title,
            amount=amount,
            category_id=kwargs.get('category_id'),
            description=kwargs.get('description'),
            currency=kwargs.get('currency', 'INR'),
            expense_date=kwargs.get('expense_date', datetime.utcnow()),
            payment_method=kwargs.get('payment_method'),
            receipt_url=kwargs.get('receipt_url'),
            vendor_name=kwargs.get('vendor_name'),
            location=kwargs.get('location'),
            is_split=kwargs.get('is_split', False),
            split_type=kwargs.get('split_type', 'equal'),
            notes=kwargs.get('notes')
        )
        
        db.session.add(expense)
        db.session.flush()  # Get the expense ID
        
        # Handle splits if applicable
        if expense.is_split:
            splits_data = kwargs.get('splits', [])
            ExpenseService._create_expense_splits(
                expense, 
                splits_data, 
                expense.split_type
            )
        
        # Update budget category spent amount
        if expense.category_id:
            category = BudgetCategory.query.get(expense.category_id)
            if category:
                category.spent_amount += amount
                category.updated_at = datetime.utcnow()
        
        db.session.commit()
        return expense
    
    @staticmethod
    def _create_expense_splits(expense, splits_data, split_type):
        """
        Create expense splits based on split type
        
        Args:
            expense: Expense object
            splits_data: List of split information
            split_type: Type of split (equal, percentage, custom)
        """
        if split_type == 'equal':
            # Split equally among all participants
            num_people = len(splits_data)
            if num_people == 0:
                return
            
            amount_per_person = expense.amount / num_people
            for split_info in splits_data:
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=split_info['user_id'],
                    amount=amount_per_person,
                    percentage=100.0 / num_people,
                    notes=split_info.get('notes')
                )
                db.session.add(split)
                
        elif split_type == 'percentage':
            # Split by percentage
            for split_info in splits_data:
                percentage = split_info.get('percentage', 0)
                amount = (expense.amount * percentage) / 100
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=split_info['user_id'],
                    amount=amount,
                    percentage=percentage,
                    notes=split_info.get('notes')
                )
                db.session.add(split)
                
        elif split_type == 'custom':
            # Custom amounts for each person
            for split_info in splits_data:
                split = ExpenseSplit(
                    expense_id=expense.id,
                    user_id=split_info['user_id'],
                    amount=split_info['amount'],
                    notes=split_info.get('notes')
                )
                db.session.add(split)
    
    @staticmethod
    def get_trip_expenses(trip_id, filters=None):
        """
        Get all expenses for a trip with optional filters
        
        Args:
            trip_id: ID of the trip
            filters: Optional filters (category_id, paid_by, is_settled, etc.)
            
        Returns:
            List of expenses
        """
        query = Expense.query.filter_by(trip_id=trip_id)
        
        if filters:
            if 'category_id' in filters:
                query = query.filter_by(category_id=filters['category_id'])
            if 'paid_by' in filters:
                query = query.filter_by(paid_by=filters['paid_by'])
            if 'is_settled' in filters:
                query = query.filter_by(is_settled=filters['is_settled'])
            if 'start_date' in filters:
                query = query.filter(Expense.expense_date >= filters['start_date'])
            if 'end_date' in filters:
                query = query.filter(Expense.expense_date <= filters['end_date'])
        
        return query.order_by(Expense.expense_date.desc()).all()
    
    @staticmethod
    def update_expense(expense_id, **kwargs):
        """
        Update an existing expense
        
        Args:
            expense_id: ID of expense to update
            **kwargs: Fields to update
            
        Returns:
            Updated expense object
        """
        expense = Expense.query.get(expense_id)
        if not expense:
            return None
        
        # Store old amount for budget update
        old_amount = expense.amount
        old_category_id = expense.category_id
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(expense, key) and key not in ['id', 'created_at']:
                setattr(expense, key, value)
        
        expense.updated_at = datetime.utcnow()
        
        # Update budget categories if amount or category changed
        if old_amount != expense.amount or old_category_id != expense.category_id:
            # Subtract from old category
            if old_category_id:
                old_category = BudgetCategory.query.get(old_category_id)
                if old_category:
                    old_category.spent_amount -= old_amount
                    old_category.updated_at = datetime.utcnow()
            
            # Add to new category
            if expense.category_id:
                new_category = BudgetCategory.query.get(expense.category_id)
                if new_category:
                    new_category.spent_amount += expense.amount
                    new_category.updated_at = datetime.utcnow()
        
        db.session.commit()
        return expense
    
    @staticmethod
    def delete_expense(expense_id):
        """
        Delete an expense and update budget category
        
        Args:
            expense_id: ID of expense to delete
            
        Returns:
            True if deleted successfully
        """
        expense = Expense.query.get(expense_id)
        if not expense:
            return False
        
        # Update budget category
        if expense.category_id:
            category = BudgetCategory.query.get(expense.category_id)
            if category:
                category.spent_amount -= expense.amount
                category.updated_at = datetime.utcnow()
        
        db.session.delete(expense)
        db.session.commit()
        return True
    
    @staticmethod
    def settle_split(split_id):
        """
        Mark an expense split as paid
        
        Args:
            split_id: ID of split to settle
            
        Returns:
            Updated split object
        """
        split = ExpenseSplit.query.get(split_id)
        if not split:
            return None
        
        split.is_paid = True
        split.paid_at = datetime.utcnow()
        
        # Check if all splits are paid
        expense = split.expense
        all_paid = all(s.is_paid for s in expense.splits)
        if all_paid:
            expense.is_settled = True
        
        db.session.commit()
        return split
    
    @staticmethod
    def create_budget_category(trip_id, category, allocated_amount, **kwargs):
        """
        Create a budget category for a trip
        
        Args:
            trip_id: ID of the trip
            category: Category name
            allocated_amount: Budget allocated for this category
            **kwargs: Additional fields
            
        Returns:
            Created budget category
        """
        budget = BudgetCategory(
            trip_id=trip_id,
            category=category,
            allocated_amount=allocated_amount,
            currency=kwargs.get('currency', 'INR'),
            notes=kwargs.get('notes')
        )
        
        db.session.add(budget)
        db.session.commit()
        return budget
    
    @staticmethod
    def get_trip_budget(trip_id):
        """
        Get budget overview for a trip
        
        Args:
            trip_id: ID of the trip
            
        Returns:
            Dictionary with budget summary
        """
        categories = BudgetCategory.query.filter_by(trip_id=trip_id).all()
        
        total_allocated = sum(c.allocated_amount for c in categories)
        total_spent = sum(c.spent_amount for c in categories)
        
        return {
            'total_allocated': total_allocated,
            'total_spent': total_spent,
            'total_remaining': total_allocated - total_spent,
            'percentage_used': (total_spent / total_allocated * 100) if total_allocated > 0 else 0,
            'categories': [c.to_dict() for c in categories],
            'is_over_budget': total_spent > total_allocated
        }
    
    @staticmethod
    def _update_budget_category(category_id, **kwargs):
        """
        Update a budget category
        
        Args:
            category_id: ID of category to update
            **kwargs: Fields to update
            
        Returns:
            Updated category
        """
        category = BudgetCategory.query.get(category_id)
        if not category:
            return None
        
        for key, value in kwargs.items():
            if hasattr(category, key) and key not in ['id', 'spent_amount', 'created_at']:
                setattr(category, key, value)
        
        category.updated_at = datetime.utcnow()
        db.session.commit()
        return category
    
    @staticmethod
    def get_expense_analytics(trip_id):
        """
        Get comprehensive expense analytics for a trip
        
        Args:
            trip_id: ID of the trip
            
        Returns:
            Dictionary with analytics data
        """
        expenses = Expense.query.filter_by(trip_id=trip_id).all()
        
        if not expenses:
            return {
                'total_expenses': 0,
                'expense_count': 0,
                'average_expense': 0,
                'by_category': {},
                'by_user': {},
                'by_payment_method': {},
                'settled_vs_unsettled': {
                    'settled': 0,
                    'unsettled': 0
                }
            }
        
        total = sum(e.amount for e in expenses)
        count = len(expenses)
        
        # By category
        by_category = {}
        for expense in expenses:
            if expense.category_id:
                cat_name = expense.budget_category_rel.category
                if cat_name not in by_category:
                    by_category[cat_name] = {'total': 0, 'count': 0}
                by_category[cat_name]['total'] += expense.amount
                by_category[cat_name]['count'] += 1
        
        # By user (who paid)
        by_user = {}
        for expense in expenses:
            username = expense.payer.username
            if username not in by_user:
                by_user[username] = {'total': 0, 'count': 0}
            by_user[username]['total'] += expense.amount
            by_user[username]['count'] += 1
        
        # By payment method
        by_payment = {}
        for expense in expenses:
            method = expense.payment_method or 'Unknown'
            if method not in by_payment:
                by_payment[method] = {'total': 0, 'count': 0}
            by_payment[method]['total'] += expense.amount
            by_payment[method]['count'] += 1
        
        # Settled vs unsettled
        settled = sum(e.amount for e in expenses if e.is_settled)
        unsettled = total - settled
        
        return {
            'total_expenses': total,
            'expense_count': count,
            'average_expense': total / count if count > 0 else 0,
            'by_category': by_category,
            'by_user': by_user,
            'by_payment_method': by_payment,
            'settled_vs_unsettled': {
                'settled': settled,
                'unsettled': unsettled,
                'settled_percentage': (settled / total * 100) if total > 0 else 0
            }
        }
    
    @staticmethod
    def calculate_settlements(trip_id):
        """
        Calculate who owes whom in a trip
        Uses simplified debt algorithm to minimize number of transactions
        
        Args:
            trip_id: ID of the trip
            
        Returns:
            List of settlement suggestions
        """
        expenses = Expense.query.filter_by(trip_id=trip_id, is_split=True).all()
        
        # Calculate balances: positive = owed money, negative = owes money
        balances = {}
        
        for expense in expenses:
            payer_id = expense.paid_by
            
            # Payer gets credited for full amount
            if payer_id not in balances:
                balances[payer_id] = 0
            balances[payer_id] += expense.amount
            
            # Each split participant owes their share
            for split in expense.splits:
                if split.user_id not in balances:
                    balances[split.user_id] = 0
                balances[split.user_id] -= split.amount
        
        # Simplify settlements
        settlements = ExpenseService._simplify_settlements(balances, trip_id)
        return settlements
    
    @staticmethod
    def _simplify_settlements(balances, trip_id):
        """
        Simplify settlements to minimize number of transactions
        
        Args:
            balances: Dictionary of user_id -> balance
            trip_id: ID of the trip
            
        Returns:
            List of settlement dictionaries
        """
        # Separate creditors (positive balance) and debtors (negative balance)
        creditors = [(uid, amt) for uid, amt in balances.items() if amt > 0.01]
        debtors = [(uid, amt) for uid, amt in balances.items() if amt < -0.01]
        
        settlements = []
        
        # Sort creditors descending, debtors ascending
        creditors.sort(key=lambda x: x[1], reverse=True)
        debtors.sort(key=lambda x: x[1])
        
        i, j = 0, 0
        while i < len(creditors) and j < len(debtors):
            creditor_id, credit = creditors[i]
            debtor_id, debt = debtors[j]
            
            # Amount to settle is minimum of what creditor is owed and debtor owes
            amount = min(credit, abs(debt))
            
            if amount > 0.01:  # Only create settlement if amount is significant
                user_from = User.query.get(debtor_id)
                user_to = User.query.get(creditor_id)
                
                settlements.append({
                    'from_user_id': debtor_id,
                    'from_username': user_from.username if user_from else None,
                    'to_user_id': creditor_id,
                    'to_username': user_to.username if user_to else None,
                    'amount': round(amount, 2)
                })
            
            # Update balances
            creditors[i] = (creditor_id, credit - amount)
            debtors[j] = (debtor_id, debt + amount)
            
            # Move to next if settled
            if creditors[i][1] < 0.01:
                i += 1
            if abs(debtors[j][1]) < 0.01:
                j += 1
        
        return settlements
    
    @staticmethod
    def create_settlement(trip_id, from_user_id, to_user_id, amount, **kwargs):
        """
        Create a settlement record
        
        Args:
            trip_id: ID of the trip
            from_user_id: User who owes money
            to_user_id: User who is owed money
            amount: Settlement amount
            **kwargs: Additional fields
            
        Returns:
            Created settlement
        """
        settlement = Settlement(
            trip_id=trip_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            amount=amount,
            currency=kwargs.get('currency', 'INR'),
            payment_method=kwargs.get('payment_method'),
            notes=kwargs.get('notes')
        )
        
        db.session.add(settlement)
        db.session.commit()
        return settlement
    
    @staticmethod
    def mark_settlement_paid(settlement_id):
        """
        Mark a settlement as paid
        
        Args:
            settlement_id: ID of settlement
            
        Returns:
            Updated settlement
        """
        settlement = Settlement.query.get(settlement_id)
        if not settlement:
            return None
        
        settlement.is_settled = True
        settlement.settled_at = datetime.utcnow()
        settlement.updated_at = datetime.utcnow()
        
        db.session.commit()
        return settlement
    
    @staticmethod
    def get_trip_settlements(trip_id, settled=None):
        """
        Get settlements for a trip
        
        Args:
            trip_id: ID of the trip
            settled: Optional filter for settled status (True/False/None)
            
        Returns:
            List of settlements
        """
        query = Settlement.query.filter_by(trip_id=trip_id)
        
        if settled is not None:
            query = query.filter_by(is_settled=settled)
        
        return query.order_by(Settlement.created_at.desc()).all()
