"""
pos/services/etims.py
KRA eTIMS Integration Service for GetCore ERP.

This module provides the interface for fiscalising sales via Kenya Revenue
Authority's eTIMS (Electronic Tax Invoice Management System).

Current state: STUB — ready for real API credentials.

Integration steps when going live:
  1. Obtain eTIMS API credentials from KRA portal (itax.kra.go.ke).
  2. Store credentials in SystemSetting or environment variables.
  3. Replace the placeholder URL and payload structure below with the
     actual KRA eTIMS API contract (REST or SOAP, per KRA spec).
  4. Set SystemSetting.enable_etims = True in the admin panel.

Reference: KRA eTIMS Developer Guide (Kenya Revenue Authority, 2023)
"""

import json
import logging
import hashlib
import hmac
from decimal import Decimal
from datetime import datetime

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────
ETIMS_API_BASE = 'https://etims-api.kra.go.ke/etims-api'   # Live endpoint
ETIMS_API_BASE_SANDBOX = 'https://etims-sbx.kra.go.ke/etims-api'  # Sandbox

ETIMS_ENDPOINTS = {
    'initialize': '/initialize',
    'save_purchase': '/trnsPurchaseSave',
    'save_sale': '/trnsSalesSave',
    'select_item': '/selectItemList',
}


class ETIMSError(Exception):
    """Raised when eTIMS API returns an error or is unreachable."""
    pass


class ETIMSService:
    """
    Handles all communication with the KRA eTIMS API.

    Usage:
        service = ETIMSService(kra_pin='P0512345678A', device_serial='VSCU001')
        result = service.fiscalise_sale(sale)
        # result = {'kra_invoice_number': '...', 'qr_code_url': '...', 'fiscal_signature': '...'}
    """

    def __init__(self, kra_pin: str, device_serial: str = None, sandbox: bool = True):
        self.kra_pin = kra_pin
        self.device_serial = device_serial or 'GETCORE-VSCU-001'
        self.base_url = ETIMS_API_BASE_SANDBOX if sandbox else ETIMS_API_BASE

    def fiscalise_sale(self, sale) -> dict:
        """
        Send a completed Sale to KRA eTIMS for fiscalisation.

        Args:
            sale: A pos.models.Sale instance (must be status='completed').

        Returns:
            dict with keys: kra_invoice_number, qr_code_url, fiscal_signature

        Raises:
            ETIMSError: on API failure or invalid response.
        """
        if sale.status != 'completed':
            raise ETIMSError(f'Cannot fiscalise sale {sale.invoice_number}: status is {sale.status}')

        payload = self._build_sale_payload(sale)

        logger.info(f'[eTIMS] Fiscalising sale {sale.invoice_number} for KRA PIN {self.kra_pin}')

        # ── STUB: Replace with real HTTP call when live ──────────────────
        # In production, use:
        #   import requests
        #   response = requests.post(
        #       f'{self.base_url}{ETIMS_ENDPOINTS["save_sale"]}',
        #       json=payload,
        #       headers=self._build_headers(),
        #       timeout=30
        #   )
        #   response.raise_for_status()
        #   data = response.json()
        #   return self._parse_response(data, sale)
        # ────────────────────────────────────────────────────────────────

        # Stub response for development / testing
        stub_result = {
            'kra_invoice_number': f'KRA-{sale.invoice_number}',
            'qr_code_url': f'https://etims.kra.go.ke/verify?inv={sale.invoice_number}',
            'fiscal_signature': self._generate_stub_signature(sale),
        }
        logger.info(f'[eTIMS STUB] Mock fiscalisation for {sale.invoice_number}: {stub_result}')
        return stub_result

    def _build_sale_payload(self, sale) -> dict:
        """Build the eTIMS-compliant JSON payload for a sale."""
        items = []
        for item in sale.items.all():
            items.append({
                'itemSeq': item.pk,
                'itemCd': item.product.sku or f'ITEM{item.product.pk}',
                'itemNm': item.product_name,
                'qty': float(item.quantity),
                'prc': float(item.unit_price),
                'splyAmt': float(item.line_total),
                'taxTyCd': 'B' if not item.is_vat_exempt else 'E',   # B=VAT, E=Exempt
                'taxAmt': float(item.line_total * Decimal('0.16')) if not item.is_vat_exempt else 0,
                'totAmt': float(item.line_total),
            })

        return {
            'tin': self.kra_pin,
            'bhfId': self.device_serial,
            'invcNo': sale.invoice_number,
            'orgInvcNo': '',
            'salesTyCd': 'N',  # N=Normal
            'rcptTyCd': 'S',   # S=Sale
            'pmtTyCd': self._map_payment_type(sale.payment_method),
            'salesSttsCd': '02',  # 02=Approved
            'cfmDt': sale.created_at.strftime('%Y%m%d%H%M%S'),
            'salesDt': sale.created_at.strftime('%Y%m%d'),
            'custTin': sale.customer.kra_pin if sale.customer and sale.customer.kra_pin else None,
            'custNm': sale.customer.name if sale.customer else 'Walk-in',
            'totItemCnt': sale.items.count(),
            'taxblAmtA': 0,
            'taxblAmtB': float(sale.subtotal - sale.discount_amount),
            'taxRtA': 0,
            'taxRtB': 16,
            'taxAmtA': 0,
            'taxAmtB': float(sale.vat_amount),
            'totTaxblAmt': float(sale.subtotal - sale.discount_amount),
            'totTaxAmt': float(sale.vat_amount),
            'totAmt': float(sale.total_amount),
            'itemList': items,
        }

    def _map_payment_type(self, method: str) -> str:
        """Map GetCore payment method to KRA eTIMS payment type code."""
        mapping = {
            'cash': '01',
            'card': '02',
            'mpesa': '03',   # Mobile Money
            'credit': '04',
            'split': '05',
        }
        return mapping.get(method, '01')

    def _build_headers(self) -> dict:
        """Build HTTP headers for eTIMS API requests."""
        return {
            'Content-Type': 'application/json',
            'tin': self.kra_pin,
            'bhfId': self.device_serial,
        }

    def _parse_response(self, data: dict, sale) -> dict:
        """Parse KRA eTIMS API response and extract fiscalisation details."""
        result_code = data.get('resultCd', '')
        if result_code != '000':
            raise ETIMSError(
                f'eTIMS error {result_code}: {data.get("resultMsg", "Unknown error")}'
            )
        result_data = data.get('data', {})
        return {
            'kra_invoice_number': result_data.get('rcptNo', ''),
            'qr_code_url': result_data.get('intrlData', ''),
            'fiscal_signature': result_data.get('rcptSign', ''),
        }

    def _generate_stub_signature(self, sale) -> str:
        """Generate a deterministic stub signature for development."""
        raw = f'{self.kra_pin}:{sale.invoice_number}:{sale.total_amount}'
        return hashlib.sha256(raw.encode()).hexdigest()[:32].upper()


def fiscalise_sale_if_enabled(sale):
    """
    Convenience function. Called from pos/views.py after saving a sale.
    Checks if eTIMS is enabled in SystemSetting before attempting fiscalisation.
    Silently logs errors — never raises to avoid breaking the POS flow.

    Args:
        sale: A pos.models.Sale instance.
    """
    try:
        from settings_app.models import SystemSetting
        sys_settings = SystemSetting.get_settings(getattr(sale, 'tenant', None))

        if not sys_settings.enable_etims:
            logger.debug('[eTIMS] eTIMS disabled in SystemSetting. Skipping.')
            return

        if not sys_settings.kra_pin:
            logger.warning('[eTIMS] KRA PIN not configured. Cannot fiscalise.')
            return

        service = ETIMSService(
            kra_pin=sys_settings.kra_pin,
            sandbox=True,   # Set to False in production
        )
        result = service.fiscalise_sale(sale)

        # Persist fiscalisation data to the sale record
        sale.kra_invoice_number = result['kra_invoice_number']
        sale.qr_code_url = result['qr_code_url']
        sale.fiscal_signature = result['fiscal_signature']
        sale.is_fiscalized = True
        sale.save(update_fields=['kra_invoice_number', 'qr_code_url', 'fiscal_signature', 'is_fiscalized'])

        logger.info(f'[eTIMS] Sale {sale.invoice_number} fiscalised: {result["kra_invoice_number"]}')

    except ETIMSError as e:
        logger.error(f'[eTIMS] Fiscalisation failed for {sale.invoice_number}: {e}')
    except Exception as e:
        logger.exception(f'[eTIMS] Unexpected error fiscalising {sale.invoice_number}: {e}')
