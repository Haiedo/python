"""
VNPay Payment Gateway Configuration
"""
import hashlib
import hmac
import urllib.parse
from datetime import datetime

VNPAY_TMN_CODE = 'B77INC60'
VNPAY_HASH_SECRET = 'NU3W61XPNAW4DDRSYM30E0G4GL97VG7M'
VNPAY_URL = 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'
VNPAY_RETURN_URL = 'http://localhost:5000/api/payments/vnpay-return'
VNPAY_API_URL = 'https://sandbox.vnpayment.vn/merchant_webapi/api/transaction'
VNPAY_ENV = 'sandbox'


def sort_object(obj):
    """
    Sort object and encode values like VNPay demo
    Convert spaces to + instead of %20
    """
    sorted_dict = {}
    sorted_keys = sorted(obj.keys())

    for key in sorted_keys:
        value = str(obj[key])
        encoded = urllib.parse.quote_plus(value)
        sorted_dict[key] = encoded

    return sorted_dict


def create_payment_url(order_id, amount, order_desc, ip_addr):
    """
    Create VNPay payment URL following VNPay demo exactly

    Args:
        order_id: Unique order ID
        amount: Payment amount (VND)
        order_desc: Order description
        ip_addr: Customer IP address

    Returns:
        Payment URL string
    """
    from datetime import timedelta

    now = datetime.now()
    create_date = now.strftime('%Y%m%d%H%M%S')

    input_data = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': VNPAY_TMN_CODE,
        'vnp_Amount': int(amount * 100),
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': order_id,
        'vnp_OrderInfo': order_desc,
        'vnp_OrderType': 'other',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': VNPAY_RETURN_URL,
        'vnp_IpAddr': ip_addr,
        'vnp_CreateDate': create_date
    }

    sorted_data = sort_object(input_data)

    sign_data_parts = []
    for key in sorted(sorted_data.keys()):
        sign_data_parts.append(f"{key}={sorted_data[key]}")

    sign_data = '&'.join(sign_data_parts)

    h = hmac.new(
        VNPAY_HASH_SECRET.encode('utf-8'),
        sign_data.encode('utf-8'),
        hashlib.sha512
    )
    vnp_secure_hash = h.hexdigest()

    payment_url = f"{VNPAY_URL}?{sign_data}&vnp_SecureHash={vnp_secure_hash}"

    return payment_url


def validate_response(params):
    """
    Validate VNPay response

    Args:
        params: Dictionary of query parameters from VNPay

    Returns:
        (is_valid, response_data)
    """
    vnp_secure_hash = params.get('vnp_SecureHash')

    if not vnp_secure_hash:
        return False, None

    input_data = {}
    for key, value in params.items():
        if key not in ['vnp_SecureHash', 'vnp_SecureHashType']:
            input_data[key] = value

    sorted_keys = sorted(input_data.keys())
    hash_data_parts = []
    for key in sorted_keys:
        hash_data_parts.append(f"{key}={input_data[key]}")

    hash_data = '&'.join(hash_data_parts)

    calculated_hash = hmac.new(
        VNPAY_HASH_SECRET.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    is_valid = calculated_hash == vnp_secure_hash

    response_data = {
        'transaction_id': params.get('vnp_TxnRef'),
        'amount': int(params.get('vnp_Amount', 0)) / 100,
        'order_info': params.get('vnp_OrderInfo'),
        'response_code': params.get('vnp_ResponseCode'),
        'transaction_no': params.get('vnp_TransactionNo'),
        'bank_code': params.get('vnp_BankCode'),
        'pay_date': params.get('vnp_PayDate')
    }

    return is_valid, response_data
