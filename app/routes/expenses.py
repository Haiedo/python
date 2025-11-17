from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.expense import Expense, ExpenseSplit
from app.models.group import Group, GroupMember
from app.models.category import Category
from app.utils.decorators import group_admin_required, group_member_required
from decimal import Decimal

bp = Blueprint('expenses', __name__, url_prefix='/api/expenses')


def calculate_splits(expense, split_data, split_type):
    """Calculate and create expense splits"""
    splits = []
    total_amount = Decimal(str(expense.amount))

    if split_type == 'equal':
        # Equal split among all members
        member_ids = [m.user_id for m in expense.group.members]
        split_amount = total_amount / len(member_ids)

        for user_id in member_ids:
            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=user_id,
                amount=split_amount,
                percentage=Decimal('100') / len(member_ids)
            )
            splits.append(split)

    elif split_type == 'unequal':
        # Unequal split with percentages
        if not split_data:
            raise ValueError('Split data required for unequal split')

        total_percentage = sum(Decimal(str(s.get('percentage', 0))) for s in split_data)
        if abs(total_percentage - 100) > 0.01:
            raise ValueError('Percentages must add up to 100')

        for split_item in split_data:
            percentage = Decimal(str(split_item['percentage']))
            amount = (total_amount * percentage) / 100

            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=split_item['user_id'],
                amount=amount,
                percentage=percentage
            )
            splits.append(split)

    elif split_type == 'custom':
        # Custom split with specific amounts
        if not split_data:
            raise ValueError('Split data required for custom split')

        total_split = sum(Decimal(str(s.get('amount', 0))) for s in split_data)
        if abs(total_split - total_amount) > 0.01:
            raise ValueError('Split amounts must equal total expense amount')

        for split_item in split_data:
            amount = Decimal(str(split_item['amount']))
            percentage = (amount / total_amount) * 100

            split = ExpenseSplit(
                expense_id=expense.id,
                user_id=split_item['user_id'],
                amount=amount,
                percentage=percentage
            )
            splits.append(split)

    return splits


@bp.route('', methods=['POST'])
@jwt_required()
def create_expense():
    """Create a new expense (request for approval if client)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    # Validate required fields
    required_fields = ['group_id', 'description', 'amount', 'paid_by_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user is member of the group
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=data['group_id']
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    # Validate group
    group = Group.query.get(data['group_id'])
    if not group or not group.is_active:
        return jsonify({'error': 'Group not found'}), 404

    # Check if paid_by is a member
    payer_membership = GroupMember.query.filter_by(
        user_id=data['paid_by_id'],
        group_id=data['group_id']
    ).first()

    if not payer_membership:
        return jsonify({'error': 'Payer must be a group member'}), 400

    # Validate category if provided
    if data.get('category_id'):
        category = Category.query.get(data['category_id'])
        if not category or not category.is_active:
            return jsonify({'error': 'Invalid category'}), 400

    # Create expense
    split_type = data.get('split_type', 'equal')
    status = 'approved' if membership.role == 'admin' else 'pending'

    expense = Expense(
        group_id=data['group_id'],
        category_id=data.get('category_id'),
        created_by_id=user_id,
        description=data['description'],
        amount=Decimal(str(data['amount'])),
        currency=data.get('currency', group.currency),
        paid_by_id=data['paid_by_id'],
        split_type=split_type,
        status=status,
        receipt_url=data.get('receipt_url')
    )

    try:
        db.session.add(expense)
        db.session.flush()  # Get expense.id

        # Calculate and create splits
        splits = calculate_splits(expense, data.get('splits'), split_type)
        for split in splits:
            db.session.add(split)

        # If admin, auto-approve
        if membership.role == 'admin':
            expense.approved_by_id = user_id
            from datetime import datetime
            expense.approved_at = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'message': 'Expense created successfully',
            'expense': expense.to_dict(include_splits=True)
        }), 201

    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create expense: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_expenses():
    """Get expenses (filtered by group or all user's expenses)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status')  # pending, approved, rejected

    query = Expense.query

    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return jsonify({'error': 'You are not a member of this group'}), 403

        query = query.filter_by(group_id=group_id)
    else:
        # Get expenses from all user's groups
        user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]
        query = query.filter(Expense.group_id.in_(user_groups))

    # Filter by status
    if status:
        query = query.filter_by(status=status)

    # Order by most recent
    expenses = query.order_by(Expense.created_at.desc()).all()

    return jsonify({
        'expenses': [e.to_dict(include_splits=True) for e in expenses]
    }), 200


@bp.route('/<int:expense_id>', methods=['GET'])
@jwt_required()
def get_expense(expense_id):
    """Get expense details"""
    user_id = int(get_jwt_identity())  # Convert string to int
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check membership
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=expense.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'expense': expense.to_dict(include_splits=True)
    }), 200


@bp.route('/<int:expense_id>', methods=['PUT'])
@jwt_required()
def update_expense(expense_id):
    """Update expense (creator or admin only, before approval)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check permissions
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=expense.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    is_admin = membership.role == 'admin'
    is_creator = expense.created_by_id == user_id

    # Only creator can edit pending expenses, admin can edit any
    if not is_admin and not is_creator:
        return jsonify({'error': 'Permission denied'}), 403

    if not is_admin and expense.status != 'pending':
        return jsonify({'error': 'Can only edit pending expenses'}), 400

    data = request.get_json()

    # Update fields
    if 'description' in data:
        expense.description = data['description']

    if 'amount' in data:
        expense.amount = Decimal(str(data['amount']))

    if 'category_id' in data:
        expense.category_id = data['category_id']

    if 'receipt_url' in data:
        expense.receipt_url = data['receipt_url']

    # If splits changed, recalculate
    if 'splits' in data or 'split_type' in data:
        new_split_type = data.get('split_type', expense.split_type)

        # Delete old splits
        ExpenseSplit.query.filter_by(expense_id=expense.id).delete()

        # Create new splits
        splits = calculate_splits(expense, data.get('splits'), new_split_type)
        for split in splits:
            db.session.add(split)

        expense.split_type = new_split_type

    try:
        db.session.commit()
        return jsonify({
            'message': 'Expense updated successfully',
            'expense': expense.to_dict(include_splits=True)
        }), 200

    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/<int:expense_id>', methods=['DELETE'])
@jwt_required()
def delete_expense(expense_id):
    """Delete expense (creator can delete pending, admin can delete any)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check permissions
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=expense.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    is_admin = membership.role == 'admin'
    is_creator = expense.created_by_id == user_id

    if not is_admin and not is_creator:
        return jsonify({'error': 'Permission denied'}), 403

    if not is_admin and expense.status != 'pending':
        return jsonify({'error': 'Can only delete pending expenses'}), 400

    try:
        db.session.delete(expense)
        db.session.commit()
        return jsonify({'message': 'Expense deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@bp.route('/<int:expense_id>/approve', methods=['POST'])
@jwt_required()
def approve_expense(expense_id):
    """Approve expense (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=expense.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    if expense.status != 'pending':
        return jsonify({'error': 'Expense is not pending'}), 400

    expense.status = 'approved'
    expense.approved_by_id = user_id
    from datetime import datetime
    expense.approved_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'message': 'Expense approved successfully',
            'expense': expense.to_dict(include_splits=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Approval failed: {str(e)}'}), 500


@bp.route('/<int:expense_id>/reject', methods=['POST'])
@jwt_required()
def reject_expense(expense_id):
    """Reject expense (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=expense.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    if expense.status != 'pending':
        return jsonify({'error': 'Expense is not pending'}), 400

    expense.status = 'rejected'
    expense.approved_by_id = user_id
    from datetime import datetime
    expense.approved_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'message': 'Expense rejected',
            'expense': expense.to_dict(include_splits=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Rejection failed: {str(e)}'}), 500
