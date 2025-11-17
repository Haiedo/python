from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.recurring_expense import RecurringExpense
from app.models.group import GroupMember
from app.utils.decorators import group_admin_required

bp = Blueprint('recurring', __name__, url_prefix='/api/recurring')


@bp.route('', methods=['POST'])
@jwt_required()
def create_recurring_expense():
    """Create a recurring expense template"""
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    # Validate required fields
    required_fields = ['group_id', 'description', 'amount', 'paid_by_id', 'frequency', 'start_date']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check group membership
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=data['group_id']
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    # Only admin can create recurring expenses
    if membership.role != 'admin':
        return jsonify({'error': 'Only group admins can create recurring expenses'}), 403

    # Validate frequency
    valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
    if data['frequency'] not in valid_frequencies:
        return jsonify({'error': 'Invalid frequency'}), 400

    # Parse dates
    try:
        start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    # Create recurring expense
    recurring = RecurringExpense(
        group_id=data['group_id'],
        category_id=data.get('category_id'),
        created_by_id=user_id,
        description=data['description'],
        amount=data['amount'],
        currency=data.get('currency', 'VND'),
        paid_by_id=data['paid_by_id'],
        split_type=data.get('split_type', 'equal'),
        frequency=data['frequency'],
        interval=data.get('interval', 1),
        start_date=start_date,
        end_date=end_date,
        next_occurrence=start_date
    )

    try:
        db.session.add(recurring)
        db.session.commit()

        return jsonify({
            'message': 'Recurring expense created successfully',
            'recurring_expense': recurring.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create recurring expense: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_recurring_expenses():
    """Get recurring expenses (filtered by group)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)

    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return jsonify({'error': 'You are not a member of this group'}), 403

        recurring_expenses = RecurringExpense.query.filter_by(
            group_id=group_id
        ).order_by(RecurringExpense.created_at.desc()).all()
    else:
        # Get all user's groups
        user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]
        recurring_expenses = RecurringExpense.query.filter(
            RecurringExpense.group_id.in_(user_groups)
        ).order_by(RecurringExpense.created_at.desc()).all()

    return jsonify({
        'recurring_expenses': [r.to_dict() for r in recurring_expenses]
    }), 200


@bp.route('/<int:recurring_id>', methods=['GET'])
@jwt_required()
def get_recurring_expense(recurring_id):
    """Get recurring expense details"""
    user_id = int(get_jwt_identity())  # Convert string to int
    recurring = RecurringExpense.query.get(recurring_id)

    if not recurring:
        return jsonify({'error': 'Recurring expense not found'}), 404

    # Check membership
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=recurring.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'recurring_expense': recurring.to_dict()
    }), 200


@bp.route('/<int:recurring_id>', methods=['PUT'])
@jwt_required()
def update_recurring_expense(recurring_id):
    """Update recurring expense (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    recurring = RecurringExpense.query.get(recurring_id)

    if not recurring:
        return jsonify({'error': 'Recurring expense not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=recurring.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    data = request.get_json()

    # Update fields
    if 'description' in data:
        recurring.description = data['description']
    if 'amount' in data:
        recurring.amount = data['amount']
    if 'category_id' in data:
        recurring.category_id = data['category_id']
    if 'frequency' in data:
        recurring.frequency = data['frequency']
    if 'interval' in data:
        recurring.interval = data['interval']
    if 'end_date' in data:
        if data['end_date']:
            recurring.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        else:
            recurring.end_date = None

    try:
        db.session.commit()
        return jsonify({
            'message': 'Recurring expense updated successfully',
            'recurring_expense': recurring.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/<int:recurring_id>', methods=['DELETE'])
@jwt_required()
def delete_recurring_expense(recurring_id):
    """Delete recurring expense (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    recurring = RecurringExpense.query.get(recurring_id)

    if not recurring:
        return jsonify({'error': 'Recurring expense not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=recurring.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    try:
        db.session.delete(recurring)
        db.session.commit()
        return jsonify({'message': 'Recurring expense deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@bp.route('/<int:recurring_id>/pause', methods=['POST'])
@jwt_required()
def pause_recurring_expense(recurring_id):
    """Pause/unpause recurring expense (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    recurring = RecurringExpense.query.get(recurring_id)

    if not recurring:
        return jsonify({'error': 'Recurring expense not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=recurring.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    # Toggle pause state
    recurring.is_paused = not recurring.is_paused

    try:
        db.session.commit()
        status = 'paused' if recurring.is_paused else 'resumed'
        return jsonify({
            'message': f'Recurring expense {status} successfully',
            'recurring_expense': recurring.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to pause/resume: {str(e)}'}), 500
