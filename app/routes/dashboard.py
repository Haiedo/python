from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.group import GroupMember
from app.models.expense import Expense, ExpenseSplit
from app.models.payment import Payment
from sqlalchemy import func, or_

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


@bp.route('', methods=['GET'])
@jwt_required()
def get_user_dashboard():
    """Get user dashboard statistics"""
    from flask import current_app, request
    current_app.logger.info(f'Dashboard request headers: {dict(request.headers)}')
    user_id = int(get_jwt_identity())  # Convert string to int
    current_app.logger.info(f'User ID from JWT: {user_id}')

    # Get user's groups
    user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]

    # Total groups
    total_groups = len(user_groups)

    # Total expenses in user's groups
    total_expenses = Expense.query.filter(
        Expense.group_id.in_(user_groups),
        Expense.status == 'approved'
    ).count()

    # Expenses created by user
    expenses_created = Expense.query.filter_by(
        created_by_id=user_id,
        status='approved'
    ).count()

    # Total amount user spent (as payer)
    total_paid = db.session.query(
        func.sum(Expense.amount)
    ).filter(
        Expense.paid_by_id == user_id,
        Expense.status == 'approved'
    ).scalar() or 0

    # Total amount user owes
    total_owed = db.session.query(
        func.sum(ExpenseSplit.amount)
    ).join(Expense).filter(
        ExpenseSplit.user_id == user_id,
        Expense.status == 'approved'
    ).scalar() or 0

    # Payments made
    payments_made = Payment.query.filter_by(
        payer_id=user_id,
        status='completed'
    ).count()

    total_payments_made = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.payer_id == user_id,
        Payment.status == 'completed'
    ).scalar() or 0

    # Payments received
    payments_received = Payment.query.filter_by(
        payee_id=user_id,
        status='completed'
    ).count()

    total_payments_received = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.payee_id == user_id,
        Payment.status == 'completed'
    ).scalar() or 0

    # Calculate net balance
    net_balance = float(total_paid) - float(total_owed) + float(total_payments_made) - float(total_payments_received)

    stats = {
        'total_groups': total_groups,
        'total_expenses': total_expenses,
        'expenses_created': expenses_created,
        'total_paid': float(total_paid),
        'total_owed': float(total_owed),
        'payments_made': payments_made,
        'total_payments_made': float(total_payments_made),
        'payments_received': payments_received,
        'total_payments_received': float(total_payments_received),
        'net_balance': net_balance
    }

    return jsonify(stats), 200


@bp.route('/expenses-by-category', methods=['GET'])
@jwt_required()
def get_expenses_by_category():
    """Get user's expenses grouped by category"""
    user_id = int(get_jwt_identity())  # Convert string to int

    # Get expenses where user is involved (as splits)
    results = db.session.query(
        Expense.category_id,
        func.sum(ExpenseSplit.amount).label('total')
    ).join(ExpenseSplit).filter(
        ExpenseSplit.user_id == user_id,
        Expense.status == 'approved'
    ).group_by(Expense.category_id).all()

    from app.models.category import Category

    categories_data = []
    for category_id, total in results:
        category = Category.query.get(category_id) if category_id else None
        categories_data.append({
            'category': category.to_dict() if category else {'name': 'Uncategorized'},
            'total': float(total)
        })

    return jsonify({
        'categories': categories_data
    }), 200


@bp.route('/recent-activity', methods=['GET'])
@jwt_required()
def get_recent_activity():
    """Get user's recent expenses and payments"""
    user_id = int(get_jwt_identity())  # Convert string to int
    limit = request.args.get('limit', default=10, type=int)

    # Get user's groups
    user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]

    # Recent expenses
    recent_expenses = Expense.query.filter(
        Expense.group_id.in_(user_groups)
    ).order_by(Expense.created_at.desc()).limit(limit).all()

    # Recent payments
    recent_payments = Payment.query.filter(
        or_(Payment.payer_id == user_id, Payment.payee_id == user_id)
    ).order_by(Payment.created_at.desc()).limit(limit).all()

    return jsonify({
        'recent_expenses': [e.to_dict() for e in recent_expenses],
        'recent_payments': [p.to_dict() for p in recent_payments]
    }), 200


@bp.route('/expense-trend', methods=['GET'])
@jwt_required()
def get_expense_trend():
    """Get expense trend over time (last 30 days)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    from datetime import datetime, timedelta

    # Get user's groups
    user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]

    # Get expenses from last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Group expenses by date
    results = db.session.query(
        func.date(Expense.expense_date).label('date'),
        func.sum(ExpenseSplit.amount).label('total')
    ).join(ExpenseSplit).filter(
        ExpenseSplit.user_id == user_id,
        Expense.status == 'approved',
        Expense.expense_date >= thirty_days_ago
    ).group_by(func.date(Expense.expense_date)).order_by('date').all()

    # Format data
    trend_data = []
    for date, total in results:
        trend_data.append({
            'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
            'total': float(total)
        })

    return jsonify({
        'trend': trend_data
    }), 200
