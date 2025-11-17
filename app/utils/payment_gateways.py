"""
Payment gateway integrations (VNPay, Momo)
"""
import hashlib
import hmac
import urllib.parse
import json
import requests
from datetime import datetime
from flask import current_app


class VNPayGateway:
    """VNPay payment gateway integration"""

    def __init__(self):
        self.vnpay_url = current_app.config.get('VNPAY_URL')
        self.tmn_code = current_app.config.get('VNPAY_TMN_CODE')
        self.hash_secret = current_app.config.get('VNPAY_HASH_SECRET')

    def create_payment_url(self, order_id, amount, order_desc, return_url, ip_addr):
        """
        Create VNPay payment URL

        Args:
            order_id: Unique order ID
            amount: Amount in VND (integer)
            order_desc: Order description
            return_url: Callback URL
            ip_addr: Client IP address

        Returns:
            Payment URL string
        """
        # VNPay parameters
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.tmn_code,
            'vnp_Amount': str(int(amount * 100)),  # VNPay uses cents
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': str(order_id),
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_Locale': 'vn',
            'vnp_ReturnUrl': return_url,
            'vnp_IpAddr': ip_addr,
            'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S')
        }

        # Sort parameters
        sorted_params = sorted(vnp_params.items())

        # Create query string
        query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])

        # Create secure hash
        hash_data = '&'.join([f"{k}={v}" for k, v in sorted_params])
        secure_hash = hmac.new(
            self.hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        # Build payment URL
        payment_url = f"{self.vnpay_url}?{query_string}&vnp_SecureHash={secure_hash}"

        return payment_url

    def validate_response(self, vnp_params):
        """
        Validate VNPay callback response

        Args:
            vnp_params: Dictionary of VNPay parameters from callback

        Returns:
            tuple: (is_valid, transaction_status, message)
        """
        # Get secure hash
        vnp_secure_hash = vnp_params.get('vnp_SecureHash')
        if not vnp_secure_hash:
            return False, None, 'Missing secure hash'

        # Remove secure hash from params
        params_to_validate = {k: v for k, v in vnp_params.items() if k != 'vnp_SecureHash'}

        # Sort and create hash data
        sorted_params = sorted(params_to_validate.items())
        hash_data = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # Calculate secure hash
        calculated_hash = hmac.new(
            self.hash_secret.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

        # Validate hash
        if calculated_hash != vnp_secure_hash:
            return False, None, 'Invalid secure hash'

        # Check transaction status
        response_code = vnp_params.get('vnp_ResponseCode')
        transaction_status = vnp_params.get('vnp_TransactionStatus')

        if response_code == '00' and transaction_status == '00':
            return True, 'success', 'Transaction successful'
        else:
            return True, 'failed', f'Transaction failed: {response_code}'


class MomoGateway:
    """Momo e-wallet payment gateway integration"""

    def __init__(self):
        self.endpoint = current_app.config.get('MOMO_ENDPOINT')
        self.partner_code = current_app.config.get('MOMO_PARTNER_CODE')
        self.access_key = current_app.config.get('MOMO_ACCESS_KEY')
        self.secret_key = current_app.config.get('MOMO_SECRET_KEY')

    def create_payment(self, order_id, amount, order_info, return_url, notify_url):
        """
        Create Momo payment request

        Args:
            order_id: Unique order ID
            amount: Amount in VND (integer)
            order_info: Order description
            return_url: Return URL after payment
            notify_url: Webhook URL for payment notification

        Returns:
            dict: Response from Momo API with payment URL
        """
        request_id = f"REQ_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Momo request data
        raw_data = {
            'partnerCode': self.partner_code,
            'partnerName': 'Expense Splitter',
            'storeId': 'ExpenseSplitter',
            'requestId': request_id,
            'amount': str(int(amount)),
            'orderId': str(order_id),
            'orderInfo': order_info,
            'redirectUrl': return_url,
            'ipnUrl': notify_url,
            'lang': 'vi',
            'requestType': 'captureWallet',
            'autoCapture': True,
            'extraData': ''
        }

        # Create signature
        raw_signature = (
            f"accessKey={self.access_key}"
            f"&amount={raw_data['amount']}"
            f"&extraData={raw_data['extraData']}"
            f"&ipnUrl={raw_data['ipnUrl']}"
            f"&orderId={raw_data['orderId']}"
            f"&orderInfo={raw_data['orderInfo']}"
            f"&partnerCode={raw_data['partnerCode']}"
            f"&redirectUrl={raw_data['redirectUrl']}"
            f"&requestId={raw_data['requestId']}"
            f"&requestType={raw_data['requestType']}"
        )

        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            raw_signature.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Add signature to request
        raw_data['signature'] = signature

        try:
            # Send request to Momo
            response = requests.post(
                self.endpoint,
                json=raw_data,
                headers={'Content-Type': 'application/json'}
            )

            result = response.json()

            return {
                'success': result.get('resultCode') == 0,
                'payment_url': result.get('payUrl'),
                'message': result.get('message'),
                'request_id': request_id,
                'result': result
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Momo API error: {str(e)}'
            }

    def validate_callback(self, momo_params):
        """
        Validate Momo payment callback

        Args:
            momo_params: Dictionary of Momo parameters from callback

        Returns:
            tuple: (is_valid, transaction_status, message)
        """
        # Get signature
        received_signature = momo_params.get('signature')
        if not received_signature:
            return False, None, 'Missing signature'

        # Create signature string
        raw_signature = (
            f"accessKey={self.access_key}"
            f"&amount={momo_params.get('amount')}"
            f"&extraData={momo_params.get('extraData', '')}"
            f"&message={momo_params.get('message')}"
            f"&orderId={momo_params.get('orderId')}"
            f"&orderInfo={momo_params.get('orderInfo')}"
            f"&orderType={momo_params.get('orderType')}"
            f"&partnerCode={momo_params.get('partnerCode')}"
            f"&payType={momo_params.get('payType')}"
            f"&requestId={momo_params.get('requestId')}"
            f"&responseTime={momo_params.get('responseTime')}"
            f"&resultCode={momo_params.get('resultCode')}"
            f"&transId={momo_params.get('transId')}"
        )

        # Calculate signature
        calculated_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            raw_signature.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Validate
        if calculated_signature != received_signature:
            return False, None, 'Invalid signature'

        # Check result code
        result_code = int(momo_params.get('resultCode', -1))

        if result_code == 0:
            return True, 'success', 'Transaction successful'
        else:
            return True, 'failed', f'Transaction failed: {result_code}'


def create_payment_url(payment_method, payment_id, amount, description, return_url, ip_addr=None):
    """
    Create payment URL for specified gateway

    Args:
        payment_method: 'vnpay' or 'momo'
        payment_id: Payment ID
        amount: Amount to pay
        description: Payment description
        return_url: Return URL after payment
        ip_addr: Client IP (for VNPay)

    Returns:
        Payment URL string or error dict
    """
    if payment_method == 'vnpay':
        gateway = VNPayGateway()
        return gateway.create_payment_url(
            order_id=payment_id,
            amount=amount,
            order_desc=description,
            return_url=return_url,
            ip_addr=ip_addr or '127.0.0.1'
        )

    elif payment_method == 'momo':
        gateway = MomoGateway()
        notify_url = return_url  # Use same URL for now
        result = gateway.create_payment(
            order_id=payment_id,
            amount=amount,
            order_info=description,
            return_url=return_url,
            notify_url=notify_url
        )

        if result['success']:
            return result['payment_url']
        else:
            return {'error': result['message']}

    else:
        return {'error': 'Invalid payment method'}
