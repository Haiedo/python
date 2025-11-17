from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.payment import Payment
from app.models.group import GroupMember
from app.utils.decorators import group_member_required, group_admin_required
from app.utils.settlement import calculate_settlements, get_user_debts
from app.config.vnpay import create_payment_url, validate_response
from decimal import Decimal

bp = Blueprint('payments', __name__, url_prefix='/api')


@bp.route('/groups/<int:group_id>/balances', methods=['GET'])
@jwt_required()
@group_member_required
def get_group_balances(group_id):
    """Get all balances in a group"""
    from app.models.user import User

    settlements_data = calculate_settlements(group_id)

    # Format balances with full user info
    formatted_balances = {}
    for user_id_str, balance in settlements_data['balances'].items():
        user = User.query.get(int(user_id_str))
        formatted_balances[user_id_str] = {
            'balance': balance,
            'user': user.to_dict() if user else None
        }

    return jsonify({
        'balances': formatted_balances
    }), 200


@bp.route('/groups/<int:group_id>/settlements', methods=['GET'])
@jwt_required()
@group_member_required
def get_settlement_suggestions(group_id):
    """Get optimized settlement suggestions for a group"""
    from app.models.user import User

    settlements_data = calculate_settlements(group_id)

    # Format settlements with full user info
    formatted_settlements = []
    for settlement in settlements_data['settlements']:
        from_user = User.query.get(settlement['payer_id'])
        to_user = User.query.get(settlement['payee_id'])

        formatted_settlements.append({
            'from': from_user.to_dict() if from_user else None,
            'to': to_user.to_dict() if to_user else None,
            'amount': settlement['amount']
        })

    return jsonify({
        'settlements': formatted_settlements
    }), 200


@bp.route('/groups/<int:group_id>/my-debts', methods=['GET'])
@jwt_required()
@group_member_required
def get_my_debts(group_id):
    """Get current user's debts and credits in a group"""
    from app.models.user import User

    user_id = int(get_jwt_identity())  # Convert string to int
    debts_data = get_user_debts(user_id, group_id)

    # Format debts with full user info
    # Combine owes (negative) and owed (positive) into one list
    formatted_debts = []

    # Add people I owe (negative amounts)
    for debt in debts_data['owes']:
        user = User.query.get(debt['user_id'])
        formatted_debts.append({
            'user_id': debt['user_id'],
            'user': user.to_dict() if user else None,
            'amount': -debt['amount']  # Negative because I owe
        })

    # Add people who owe me (positive amounts)
    for credit in debts_data['owed']:
        user = User.query.get(credit['user_id'])
        formatted_debts.append({
            'user_id': credit['user_id'],
            'user': user.to_dict() if user else None,
            'amount': credit['amount']  # Positive because they owe me
        })

    return jsonify({
        'debts': formatted_debts,
        'net_balance': debts_data['net_balance']
    }), 200


@bp.route('/payments', methods=['POST'])
@jwt_required()
def create_payment():
    """Record a payment"""
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    # Validate required fields
    required_fields = ['group_id', 'payee_id', 'amount']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if user is member of the group
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=data['group_id']
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this group'}), 403

    # Check if payee is member
    payee_membership = GroupMember.query.filter_by(
        user_id=data['payee_id'],
        group_id=data['group_id']
    ).first()

    if not payee_membership:
        return jsonify({'error': 'Payee must be a group member'}), 400

    # Cannot pay yourself
    if user_id == data['payee_id']:
        return jsonify({'error': 'Cannot pay yourself'}), 400

    # Validate amount
    try:
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except:
        return jsonify({'error': 'Invalid amount'}), 400

    # Create payment
    payment = Payment(
        group_id=data['group_id'],
        payer_id=user_id,
        payee_id=data['payee_id'],
        amount=amount,
        currency=data.get('currency', 'VND'),
        payment_method=data.get('payment_method', 'cash'),
        notes=data.get('notes'),
        status='pending'  # Needs admin approval
    )

    try:
        db.session.add(payment)
        db.session.commit()

        return jsonify({
            'message': 'Payment recorded successfully (pending approval)',
            'payment': payment.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to record payment: {str(e)}'}), 500


@bp.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    """Get payments (filtered by group or user)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    group_id = request.args.get('group_id', type=int)
    status = request.args.get('status')  # pending, completed, failed

    query = Payment.query

    if group_id:
        # Check membership
        membership = GroupMember.query.filter_by(
            user_id=user_id,
            group_id=group_id
        ).first()

        if not membership:
            return jsonify({'error': 'You are not a member of this group'}), 403

        query = query.filter_by(group_id=group_id)

        # Non-admins can only see their own payments
        if membership.role != 'admin':
            query = query.filter(
                (Payment.payer_id == user_id) | (Payment.payee_id == user_id)
            )
    else:
        # Get user's payments from all groups
        query = query.filter(
            (Payment.payer_id == user_id) | (Payment.payee_id == user_id)
        )

    # Filter by status
    if status:
        query = query.filter_by(status=status)

    payments = query.order_by(Payment.created_at.desc()).all()

    return jsonify({
        'payments': [p.to_dict() for p in payments]
    }), 200


@bp.route('/payments/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment(payment_id):
    """Get payment details"""
    user_id = int(get_jwt_identity())  # Convert string to int
    payment = Payment.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check if user is involved or admin
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=payment.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    is_admin = membership.role == 'admin'
    is_involved = payment.payer_id == user_id or payment.payee_id == user_id

    if not is_admin and not is_involved:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'payment': payment.to_dict()
    }), 200


@bp.route('/payments/<int:payment_id>/approve', methods=['POST'])
@jwt_required()
def approve_payment(payment_id):
    """Approve a payment (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    payment = Payment.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=payment.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    if payment.status != 'pending':
        return jsonify({'error': 'Payment is not pending'}), 400

    payment.status = 'completed'
    payment.approved_by_id = user_id
    from datetime import datetime
    payment.approved_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'message': 'Payment approved successfully',
            'payment': payment.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Approval failed: {str(e)}'}), 500


@bp.route('/payments/<int:payment_id>/reject', methods=['POST'])
@jwt_required()
def reject_payment(payment_id):
    """Reject a payment (admin only)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    payment = Payment.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check admin permission
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=payment.group_id
    ).first()

    if not membership or membership.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403

    if payment.status != 'pending':
        return jsonify({'error': 'Payment is not pending'}), 400

    payment.status = 'failed'
    payment.approved_by_id = user_id
    from datetime import datetime
    payment.approved_at = datetime.utcnow()

    try:
        db.session.commit()
        return jsonify({
            'message': 'Payment rejected',
            'payment': payment.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Rejection failed: {str(e)}'}), 500


@bp.route('/payments/<int:payment_id>', methods=['DELETE'])
@jwt_required()
def delete_payment(payment_id):
    """Delete a payment (creator or admin, only if pending)"""
    user_id = int(get_jwt_identity())  # Convert string to int
    payment = Payment.query.get(payment_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check permissions
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=payment.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    is_admin = membership.role == 'admin'
    is_payer = payment.payer_id == user_id

    if not is_admin and not is_payer:
        return jsonify({'error': 'Permission denied'}), 403

    if payment.status != 'pending':
        return jsonify({'error': 'Can only delete pending payments'}), 400

    try:
        db.session.delete(payment)
        db.session.commit()
        return jsonify({'message': 'Payment deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@bp.route('/payments/vnpay-create', methods=['POST'])
@jwt_required()
def create_vnpay_payment():
    """Create VNPay payment URL"""
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    # Validate required fields
    required_fields = ['group_id', 'payee_id', 'amount']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate amount
    try:
        amount = Decimal(str(data['amount']))
        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
    except:
        return jsonify({'error': 'Invalid amount'}), 400

    # Create pending payment record
    payment = Payment(
        group_id=data['group_id'],
        payer_id=user_id,
        payee_id=data['payee_id'],
        amount=amount,
        currency='VND',
        payment_method='vnpay',
        notes=data.get('notes'),
        status='pending'
    )

    try:
        db.session.add(payment)
        db.session.commit()

        # Create VNPay payment URL
        order_desc = f"Payment #{payment.id} - {data.get('notes', 'Expense payment')}"
        ip_addr = request.remote_addr or '127.0.0.1'

        payment_url = create_payment_url(
            order_id=payment.id,
            amount=float(amount),
            order_desc=order_desc,
            ip_addr=ip_addr
        )

        return jsonify({
            'message': 'VNPay payment URL created',
            'payment_id': payment.id,
            'payment_url': payment_url
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create payment: {str(e)}'}), 500


@bp.route('/payments/vnpay-return', methods=['GET'])
def vnpay_return():
    """Handle VNPay payment return (NO JWT required - public callback)"""
    params = dict(request.args)

    try:
        payment_id = int(params.get('vnp_TxnRef'))
        response_code = params.get('vnp_ResponseCode')
        transaction_no = params.get('vnp_TransactionNo')
        amount = int(params.get('vnp_Amount', 0)) / 100

        payment = Payment.query.get(payment_id)

        if not payment:
            return f'''
            <html>
            <head>
                <title>VNPay Payment</title>
                <meta http-equiv="refresh" content="3;url=/settlements?message=vnpay_notfound">
            </head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>Không tìm thấy giao dịch</h2>
                <p>Đang chuyển về trang thanh toán...</p>
            </body>
            </html>
            '''

        # Update payment based on response code (NO signature validation)
        if response_code == '00':
            # Success
            payment.status = 'completed'
            payment.transaction_id = transaction_no
            payment.gateway_response = str(params)

            db.session.commit()

            return f'''
            <html>
            <head>
                <title>VNPay Payment Success</title>
                <meta http-equiv="refresh" content="3;url=/settlements?message=vnpay_success&payment_id={payment_id}">
            </head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2> Thanh toán thành công!</h2>
                <p>Số tiền: {amount:,.0f} VND</p>
                <p>Mã giao dịch: {transaction_no}</p>
                <p>Đang chuyển về trang thanh toán...</p>
            </body>
            </html>
            '''
        else:
            # Failed
            payment.status = 'failed'
            payment.gateway_response = str(params)

            db.session.commit()

            return f'''
            <html>
            <head>
                <title>VNPay Payment Failed</title>
                <meta http-equiv="refresh" content="3;url=/settlements?message=vnpay_failed">
            </head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h2>Thanh toán thất bại</h2>
                <p>Mã lỗi: {response_code}</p>
                <p>Đang chuyển về trang thanh toán...</p>
            </body>
            </html>
            '''

    except Exception as e:
        return f'''
        <html>
        <head>
            <title>VNPay Payment Error</title>
            <meta http-equiv="refresh" content="3;url=/settlements?message=vnpay_error">
        </head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>Lỗi xử lý thanh toán</h2>
            <p>Đang chuyển về trang thanh toán...</p>
        </body>
        </html>
        '''
