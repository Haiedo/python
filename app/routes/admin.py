from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.user import User
from app.models.group import Group
from app.models.category import Category
from app.models.expense import Expense
from app.models.payment import Payment
from app.utils.decorators import admin_required

bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def get_dashboard():
    """Get admin dashboard statistics"""
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_groups': Group.query.count(),
        'active_groups': Group.query.filter_by(is_active=True).count(),
        'total_expenses': Expense.query.count(),
        'pending_expenses': Expense.query.filter_by(status='pending').count(),
        'approved_expenses': Expense.query.filter_by(status='approved').count(),
        'total_payments': Payment.query.count(),
        'pending_payments': Payment.query.filter_by(status='pending').count(),
        'completed_payments': Payment.query.filter_by(status='completed').count()
    }

    # Calculate total expense amount
    from sqlalchemy import func
    total_expense_amount = db.session.query(
        func.sum(Expense.amount)
    ).filter_by(status='approved').scalar() or 0

    stats['total_expense_amount'] = float(total_expense_amount)

    return jsonify(stats), 200


@bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    users = User.query.all()
    return jsonify({
        'users': [u.to_dict() for u in users]
    }), 200


@bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@jwt_required()
@admin_required
def toggle_user_status(user_id):
    """Activate/deactivate user (admin only)"""
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_active = not user.is_active

    try:
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        return jsonify({
            'message': f'User {status} successfully',
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update status: {str(e)}'}), 500


@bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Get all categories"""
    categories = Category.query.filter_by(is_active=True).all()
    return jsonify({
        'categories': [c.to_dict() for c in categories]
    }), 200


@bp.route('/categories', methods=['POST'])
@jwt_required()
@admin_required
def create_category():
    """Create a new category (admin only)"""
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': 'Category name is required'}), 400

    # Check if category exists
    existing = Category.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': 'Category already exists'}), 409

    category = Category(
        name=data['name'],
        icon=data.get('icon'),
        color=data.get('color'),
        description=data.get('description')
    )

    try:
        db.session.add(category)
        db.session.commit()

        return jsonify({
            'message': 'Category created successfully',
            'category': category.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create category: {str(e)}'}), 500


@bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_category(category_id):
    """Update category (admin only)"""
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    data = request.get_json()

    if 'name' in data:
        category.name = data['name']
    if 'icon' in data:
        category.icon = data['icon']
    if 'color' in data:
        category.color = data['color']
    if 'description' in data:
        category.description = data['description']

    try:
        db.session.commit()
        return jsonify({
            'message': 'Category updated successfully',
            'category': category.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_category(category_id):
    """Delete/deactivate category (admin only)"""
    category = Category.query.get(category_id)

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    # Soft delete
    category.is_active = False

    try:
        db.session.commit()
        return jsonify({'message': 'Category deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@bp.route('/groups', methods=['GET'])
@jwt_required()
@admin_required
def get_all_groups():
    """Get all groups (admin only)"""
    groups = Group.query.all()
    return jsonify({
        'groups': [g.to_dict(include_members=True) for g in groups]
    }), 200
