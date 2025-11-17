from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.expense import Expense
from app.models.group import Group, GroupMember
from app.utils.export import export_expenses_csv, export_expenses_excel, export_expenses_pdf, export_settlements_pdf
from app.utils.settlement import calculate_settlements

bp = Blueprint('exports', __name__, url_prefix='/api/exports')


@bp.route('/expenses/csv', methods=['GET'])
@jwt_required()
def export_expenses_as_csv():
    """Export expenses to CSV"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)

    # Get expenses
    query = Expense.query

    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return {'error': 'You are not a member of this group'}, 403

        query = query.filter_by(group_id=group_id)
    else:
        # Get user's groups
        user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]
        query = query.filter(Expense.group_id.in_(user_groups))

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    expenses = query.order_by(Expense.expense_date.desc()).all()

    # Export to CSV
    csv_file = export_expenses_csv(expenses)

    filename = f'expenses_{group_id if group_id else "all"}.csv'

    return send_file(
        csv_file,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/expenses/excel', methods=['GET'])
@jwt_required()
def export_expenses_as_excel():
    """Export expenses to Excel"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)

    # Get expenses
    query = Expense.query

    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return {'error': 'You are not a member of this group'}, 403

        query = query.filter_by(group_id=group_id)
    else:
        # Get user's groups
        user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]
        query = query.filter(Expense.group_id.in_(user_groups))

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    expenses = query.order_by(Expense.expense_date.desc()).all()

    # Export to Excel
    excel_file = export_expenses_excel(expenses)

    filename = f'expenses_{group_id if group_id else "all"}.xlsx'

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/expenses/pdf', methods=['GET'])
@jwt_required()
def export_expenses_as_pdf():
    """Export expenses to PDF"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)

    # Get expenses
    query = Expense.query

    group_name = None
    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return {'error': 'You are not a member of this group'}, 403

        group = Group.query.get(group_id)
        group_name = group.name if group else None

        query = query.filter_by(group_id=group_id)
    else:
        # Get user's groups
        user_groups = [m.group_id for m in GroupMember.query.filter_by(user_id=user_id).all()]
        query = query.filter(Expense.group_id.in_(user_groups))

    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)

    expenses = query.order_by(Expense.expense_date.desc()).all()

    # Export to PDF
    pdf_file = export_expenses_pdf(expenses, group_name)

    filename = f'expenses_{group_id if group_id else "all"}.pdf'

    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/settlements/pdf', methods=['GET'])
@jwt_required()
def export_settlements_as_pdf():
    """Export settlement suggestions to PDF"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int, default=None)

    if not group_id:
        return {'error': 'group_id is required'}, 400

    # Check membership
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=group_id
    ).first()

    if not membership:
        return {'error': 'You are not a member of this group'}, 403

    # Get group
    group = Group.query.get(group_id)
    if not group:
        return {'error': 'Group not found'}, 404

    # Calculate settlements
    settlements_data = calculate_settlements(group_id)

    # Export to PDF
    pdf_file = export_settlements_pdf(settlements_data, group.name)

    filename = f'settlements_{group_id}.pdf'

    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
