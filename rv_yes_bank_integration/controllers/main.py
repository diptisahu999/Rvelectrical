# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class YesBankCallback(http.Controller):

    @http.route('/api/yesbank/callback', type='json', auth='public', methods=['POST'], csrf=False)
    def yes_bank_callback(self, **post):
        return self._process_callback(request.jsonrequest)

    @http.route('/api/yesbank/incoming', type='json', auth='public', methods=['POST'], csrf=False)
    def yes_bank_incoming(self, **post):
        data = request.jsonrequest
        data['transaction_type'] = 'CREDIT' # Force incoming
        return self._process_callback(data)

    @http.route('/api/yesbank/outgoing', type='json', auth='public', methods=['POST'], csrf=False)
    def yes_bank_outgoing(self, **post):
        data = request.jsonrequest
        data['transaction_type'] = 'DEBIT' # Force outgoing
        return self._process_callback(data)

    def _process_callback(self, data):
        """ Helper to process the payload """
        try:
            _logger.info("YES Bank Callback Received: %s", json.dumps(data))

            # 2. Log the data in the database for visibility
            amount = data.get('amount', 0.0)
            tx_type = data.get('transaction_type', '')
            
            if tx_type == 'DEBIT':
                amount = -abs(float(amount))
            elif tx_type == 'CREDIT':
                amount = abs(float(amount))
            
            request.env['yes.bank.log'].sudo().create({
                'name': f"Callback ({tx_type})",
                'amount': amount,
                'raw_data': json.dumps(data),
                'status': 'received'
            })

            return {'status': 'success', 'message': 'Callback processed'}

        except Exception as e:
            _logger.error("Error in YES Bank Callback: %s", str(e))
            return {'status': 'error', 'message': str(e)}
