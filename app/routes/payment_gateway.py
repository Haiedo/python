from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.payment import Payment
from app.models.group import GroupMember
from app.utils.payment_gateways import create_payment_url, VNPayGateway, MomoGateway
from datetime import datetime

bp = Blueprint('payment_gateway', __name__, url_prefix='/api/payment-gateway')


@bp.route('/create-payment-url', methods=['POST'])
@jwt_required()
def create_gateway_payment_url():
    """
    Create payment URL for VNPay or Momo

    Body:
        payment_id: ID of payment record
        payment_method: 'vnpay' or 'momo'
        return_url: URL to return after payment
    """
    user_id = int(get_jwt_identity())  # Convert string to int
    data = request.get_json()

    payment_id = data.get('payment_id')
    payment_method = data.get('payment_method')
    return_url = data.get('return_url')

    if not payment_id or not payment_method or not return_url:
        return jsonify({'error': 'Missing required fields'}), 400

    # Get payment
    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check if user is the payer
    if payment.payer_id != user_id:
        return jsonify({'error': 'You are not authorized to pay this'} ), 403

    # Create payment URL
    description = f"Payment #{payment.id} - {payment.notes or 'Group expense payment'}"
    ip_addr = request.remote_addr

    payment_url = create_payment_url(
        payment_method=payment_method,
        payment_id=payment.id,
        amount=float(payment.amount),
        description=description,
        return_url=return_url,
        ip_addr=ip_addr
    )

    if isinstance(payment_url, dict) and 'error' in payment_url:
        return jsonify(payment_url), 500

    # Update payment record
    payment.payment_method = payment_method
    payment.status = 'pending'
    db.session.commit()

    return jsonify({
        'payment_url': payment_url,
        'message': 'Payment URL created successfully'
    }), 200


@bp.route('/vnpay-callback', methods=['GET'])
def vnpay_callback():
    """Handle VNPay payment callback"""
    vnp_params = request.args.to_dict()

    # Validate response
    gateway = VNPayGateway()
    is_valid, status, message = gateway.validate_response(vnp_params)

    if not is_valid:
        return jsonify({
            'error': 'Invalid VNPay response',
            'message': message
        }), 400

    # Get payment
    order_id = vnp_params.get('vnp_TxnRef')
    payment = Payment.query.get(order_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Update payment status
    if status == 'success':
        payment.status = 'completed'
        payment.transaction_id = vnp_params.get('vnp_TransactionNo')
        payment.gateway_response = str(vnp_params)
        payment.payment_date = datetime.utcnow()

        db.session.commit()

        # Send email notification
        from app.utils.email_service import send_payment_confirmation
        send_payment_confirmation(
            payment.payer,
            payment.payee,
            float(payment.amount),
            payment.currency,
            payment.group.name
        )

        return jsonify({
            'success': True,
            'message': 'Payment successful',
            'payment_id': payment.id
        }), 200

    else:
        payment.status = 'failed'
        payment.gateway_response = str(vnp_params)
        db.session.commit()

        return jsonify({
            'success': False,
            'message': message
        }), 400


@bp.route('/momo-callback', methods=['POST'])
def momo_callback():
    """Handle Momo payment callback"""
    momo_params = request.get_json()

    # Validate response
    gateway = MomoGateway()
    is_valid, status, message = gateway.validate_callback(momo_params)

    if not is_valid:
        return jsonify({
            'error': 'Invalid Momo response',
            'message': message
        }), 400

    # Get payment
    order_id = momo_params.get('orderId')
    payment = Payment.query.get(order_id)

    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Update payment status
    if status == 'success':
        payment.status = 'completed'
        payment.transaction_id = momo_params.get('transId')
        payment.gateway_response = str(momo_params)
        payment.payment_date = datetime.utcnow()

        db.session.commit()

        # Send email notification
        from app.utils.email_service import send_payment_confirmation
        send_payment_confirmation(
            payment.payer,
            payment.payee,
            float(payment.amount),
            payment.currency,
            payment.group.name
        )

        return jsonify({
            'resultCode': 0,
            'message': 'Success'
        }), 200

    else:
        payment.status = 'failed'
        payment.gateway_response = str(momo_params)
        db.session.commit()

        return jsonify({
            'resultCode': 1,
            'message': message
        }), 400


@bp.route('/payment-status/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment_status(payment_id):
    """Get payment status"""
    user_id = int(get_jwt_identity())  # Convert string to int

    payment = Payment.query.get(payment_id)
    if not payment:
        return jsonify({'error': 'Payment not found'}), 404

    # Check access
    membership = GroupMember.query.filter_by(
        user_id=user_id,
        group_id=payment.group_id
    ).first()

    if not membership:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'payment_id': payment.id,
        'status': payment.status,
        'transaction_id': payment.transaction_id,
        'payment_method': payment.payment_method,
        'amount': float(payment.amount),
        'currency': payment.currency
    }), 200
