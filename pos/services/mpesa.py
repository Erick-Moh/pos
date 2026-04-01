"""
pos/services/mpesa.py
Safaricom M-Pesa Daraja API Integration for GetCore ERP.

Supports:
  - STK Push (Lipa Na M-Pesa Online) — prompts customer's phone to pay
  - Transaction status query
  - C2B (Customer to Business) callback handler

Setup checklist:
  1. Register at https://developer.safaricom.co.ke/
  2. Create an app and get Consumer Key + Consumer Secret.
  3. Go-live: apply for production credentials via Safaricom portal.
  4. Set MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET in environment or settings.
  5. Register your C2B callback URL (must be HTTPS, publicly accessible).

Current state: STUB — safe to deploy, returns mock data until credentials added.
"""

import base64
import logging
import os
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


# ── Configuration (load from environment in production) ────────────────────
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', 'YOUR_CONSUMER_KEY_HERE')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', 'YOUR_CONSUMER_SECRET_HERE')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '174379')         # Sandbox default
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', 'YOUR_PASSKEY_HERE')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://yourdomain.co.ke/pos/mpesa/callback/')

MPESA_AUTH_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
MPESA_STK_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
MPESA_QUERY_URL = 'https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query'

# Switch to production URLs when live:
# MPESA_AUTH_URL = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
# MPESA_STK_URL = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'


class MPesaError(Exception):
    """Raised when M-Pesa API returns an error or is unreachable."""
    pass


class MPesaService:
    """
    Handles STK Push and transaction queries via Safaricom Daraja API.

    Usage:
        service = MPesaService()
        result = service.stk_push(
            phone_number='254712345678',
            amount=Decimal('500.00'),
            account_ref='INV-20240101-ABC123',
            description='Payment for goods'
        )
        # result = {'checkout_request_id': '...', 'response_code': '0', ...}
    """

    def __init__(self):
        self.consumer_key = MPESA_CONSUMER_KEY
        self.consumer_secret = MPESA_CONSUMER_SECRET
        self.shortcode = MPESA_SHORTCODE
        self.passkey = MPESA_PASSKEY
        self._access_token = None

    def get_access_token(self) -> str:
        """
        Obtain OAuth2 access token from Safaricom.
        Token is valid for 3600 seconds.
        """
        # ── STUB ────────────────────────────────────────────────────────
        # In production:
        #   import requests
        #   credentials = base64.b64encode(
        #       f'{self.consumer_key}:{self.consumer_secret}'.encode()
        #   ).decode()
        #   resp = requests.get(
        #       MPESA_AUTH_URL,
        #       headers={'Authorization': f'Basic {credentials}'},
        #       timeout=15
        #   )
        #   resp.raise_for_status()
        #   return resp.json()['access_token']
        # ────────────────────────────────────────────────────────────────
        logger.debug('[M-Pesa STUB] Returning mock access token.')
        return 'STUB_ACCESS_TOKEN_REPLACE_IN_PRODUCTION'

    def _generate_password(self) -> tuple:
        """
        Generate the base64 password and timestamp required for STK push.
        Returns (password, timestamp).
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        raw = f'{self.shortcode}{self.passkey}{timestamp}'
        password = base64.b64encode(raw.encode()).decode()
        return password, timestamp

    def stk_push(
        self,
        phone_number: str,
        amount: Decimal,
        account_ref: str,
        description: str = 'Payment',
    ) -> dict:
        """
        Initiate an STK Push (Lipa Na M-Pesa Online).
        The customer receives a PIN prompt on their phone.

        Args:
            phone_number: In format '254XXXXXXXXX' (no + prefix).
            amount: Amount to charge (rounded to nearest whole number).
            account_ref: Invoice number or reference (max 12 chars).
            description: Transaction description (max 13 chars).

        Returns:
            dict with MerchantRequestID, CheckoutRequestID, ResponseCode, etc.
        """
        # Normalize phone number
        phone = str(phone_number).replace('+', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '254' + phone[1:]

        amount_int = int(round(float(amount)))
        password, timestamp = self._generate_password()

        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': amount_int,
            'PartyA': phone,
            'PartyB': self.shortcode,
            'PhoneNumber': phone,
            'CallBackURL': MPESA_CALLBACK_URL,
            'AccountReference': account_ref[:12],
            'TransactionDesc': description[:13],
        }

        logger.info(f'[M-Pesa] STK Push request: {phone} → KES {amount_int} | Ref: {account_ref}')

        # ── STUB ────────────────────────────────────────────────────────
        # In production:
        #   import requests
        #   token = self.get_access_token()
        #   resp = requests.post(
        #       MPESA_STK_URL,
        #       json=payload,
        #       headers={'Authorization': f'Bearer {token}'},
        #       timeout=30
        #   )
        #   resp.raise_for_status()
        #   return resp.json()
        # ────────────────────────────────────────────────────────────────

        stub_result = {
            'MerchantRequestID': f'GETCORE-{account_ref}-STUB',
            'CheckoutRequestID': f'ws_CO_STUB_{timestamp}',
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': 'Success. Request accepted for processing',
            '_stub': True,
        }
        logger.info(f'[M-Pesa STUB] Mock STK response: {stub_result}')
        return stub_result

    def query_stk_status(self, checkout_request_id: str) -> dict:
        """
        Check the status of a pending STK Push transaction.

        Args:
            checkout_request_id: From stk_push() response.

        Returns:
            dict with ResultCode (0 = success, 1032 = cancelled by user, etc.)
        """
        password, timestamp = self._generate_password()

        # ── STUB ────────────────────────────────────────────────────────
        logger.debug(f'[M-Pesa STUB] Query for {checkout_request_id} → returning success.')
        return {
            'ResponseCode': '0',
            'ResultCode': '0',
            'ResultDesc': 'The service request is processed successfully.',
            '_stub': True,
        }

    @staticmethod
    def parse_callback(callback_data: dict) -> dict:
        """
        Parse the STK Push callback payload sent by Safaricom to your server.
        Register this URL in Safaricom portal as your callback endpoint.

        Returns:
            dict with: success (bool), amount, phone, mpesa_receipt_number, transaction_date
        """
        try:
            body = callback_data.get('Body', {})
            stk_result = body.get('stkCallback', {})
            result_code = stk_result.get('ResultCode', -1)

            if result_code != 0:
                return {
                    'success': False,
                    'result_code': result_code,
                    'result_desc': stk_result.get('ResultDesc', 'Unknown failure'),
                }

            items = stk_result.get('CallbackMetadata', {}).get('Item', [])
            meta = {item['Name']: item.get('Value') for item in items}

            return {
                'success': True,
                'amount': Decimal(str(meta.get('Amount', 0))),
                'mpesa_receipt_number': meta.get('MpesaReceiptNumber', ''),
                'phone': str(meta.get('PhoneNumber', '')),
                'transaction_date': str(meta.get('TransactionDate', '')),
                'checkout_request_id': stk_result.get('CheckoutRequestID', ''),
            }
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f'[M-Pesa] Callback parse error: {e}')
            return {'success': False, 'error': str(e)}
