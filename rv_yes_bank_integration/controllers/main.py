# -*- coding: utf-8 -*-
import json
import logging
# pyrefly: ignore [missing-import]
from odoo import http, fields
# pyrefly: ignore [missing-import]
from odoo.http import request

_logger = logging.getLogger(__name__)

class YesBankCallback(http.Controller):

    @http.route('/api/yesbank/callback', type='http', auth='public', methods=['POST'], csrf=False)
    def yes_bank_callback(self, **post):
        try:
            data = json.loads(request.httprequest.data or '{}')
        except Exception:
            data = {}
        res = self._process_callback(data)
        return request.make_response(json.dumps(res), headers=[('Content-Type', 'application/json')])

    @http.route('/api/yesbank/incoming', type='http', auth='public', methods=['POST'], csrf=False)
    def yes_bank_incoming(self, **post):
        try:
            data = json.loads(request.httprequest.data or '{}')
        except Exception:
            data = {}
        data['transaction_type'] = 'CREDIT' # Force incoming
        res = self._process_callback(data)
        return request.make_response(json.dumps(res), headers=[('Content-Type', 'application/json')])

    @http.route('/api/yesbank/outgoing', type='http', auth='public', methods=['POST'], csrf=False)
    def yes_bank_outgoing(self, **post):
        try:
            data = json.loads(request.httprequest.data or '{}')
        except Exception:
            data = {}
        data['transaction_type'] = 'DEBIT' # Force outgoing
        res = self._process_callback(data)
        return request.make_response(json.dumps(res), headers=[('Content-Type', 'application/json')])

    def _process_callback(self, data):
        """ Helper to process the payload """
        try:
            _logger.info("YES Bank Callback Received: %s", json.dumps(data))

            # Normalize data structure
            payload = data
            if 'ftxPayCallback' in data:
                payload = data['ftxPayCallback'].get('data', {}) or data['ftxPayCallback']

            # Extract fields
            amount_str = payload.get('amount', '0.0')
            try:
                amount = abs(float(amount_str))
            except ValueError:
                amount = 0.0

            bank_ref_id = payload.get('bankRefId')
            api_ref_num = payload.get('apiRefNum')
            cust_ref_num = payload.get('custRefNum')
            txn_status = payload.get('txnStatus', 'COMPLETED')
            bene_name = payload.get('beneName')
            bene_acct_num = payload.get('beneAcctNum')

            # Determine transaction direction: CREDIT vs DEBIT
            tx_type = data.get('transaction_type') or payload.get('transaction_type')
            
            # Check Odoo settings
            get_param = request.env['ir.config_parameter'].sudo().get_param
            company_acct = get_param('rv_yes_bank_integration.yes_bank_account_number')

            if not tx_type:
                # If beneficiary account is our account number, it is CREDIT (incoming)
                if company_acct and bene_acct_num and str(bene_acct_num).strip() == str(company_acct).strip():
                    tx_type = 'CREDIT'
                # Or check if custRefNum maps to an existing outbound payment
                elif cust_ref_num:
                    try:
                        payment_id = int(cust_ref_num)
                        payment = request.env['account.payment'].sudo().search([
                            ('id', '=', payment_id),
                            ('payment_type', '=', 'outbound')
                        ], limit=1)
                        if payment:
                            tx_type = 'DEBIT'
                    except ValueError:
                        pass
                
                # Default to CREDIT if not resolved
                if not tx_type:
                    tx_type = 'CREDIT'

            # Log standard amount sign for yes.bank.log
            signed_amount = amount if tx_type == 'CREDIT' else -amount

            # 1. Update/create Odoo records
            if tx_type == 'DEBIT':
                # Process outgoing payment status update
                payment = False
                if cust_ref_num:
                    try:
                        payment = request.env['account.payment'].sudo().browse(int(cust_ref_num)).exists()
                    except ValueError:
                        pass
                if not payment and api_ref_num:
                    payment = request.env['account.payment'].sudo().search([
                        ('yes_bank_api_ref', '=', api_ref_num)
                    ], limit=1)

                if payment:
                    status_mapping = {
                        'IN_PROCESS': 'in_process',
                        'COMPLETED': 'completed',
                        'FAILED': 'failed'
                    }
                    mapped_status = status_mapping.get(txn_status, 'in_process')
                    payment.write({'yes_bank_status': mapped_status})
                    _logger.info("Updated outgoing payment %s status to %s via callback", payment.name, mapped_status)
            else:
                # Process incoming payment - Create account.payment
                # Find YES Bank journal
                Journal = request.env['account.journal'].sudo()
                yes_journal = Journal.search([('type', '=', 'bank'), ('yes_bank_balance', '!=', False)], limit=1)
                if not yes_journal and company_acct:
                    yes_journal = Journal.search([('type', '=', 'bank'), ('bank_account_id.acc_number', '=', company_acct)], limit=1)
                if not yes_journal:
                    yes_journal = Journal.search([('type', '=', 'bank'), ('code', '=', 'YES')], limit=1)
                if not yes_journal:
                    yes_journal = Journal.search([('type', '=', 'bank'), ('name', 'ilike', 'yes')], limit=1)
                if not yes_journal:
                    yes_journal = Journal.search([('type', '=', 'bank')], limit=1)

                if yes_journal:
                    # Check if this incoming payment was already processed
                    existing_payment = request.env['account.payment'].sudo().search([
                        ('payment_type', '=', 'inbound'),
                        ('yes_bank_ref_id', '=', bank_ref_id)
                    ], limit=1) if bank_ref_id else False

                    if not existing_payment:
                        # Try to match partner by name
                        partner = False
                        if bene_name:
                            partner = request.env['res.partner'].sudo().search([('name', 'ilike', bene_name)], limit=1)

                        # Find payment method line
                        pay_method_line = yes_journal.inbound_payment_method_line_ids.filtered(lambda l: l.code == 'manual')
                        if not pay_method_line:
                            pay_method_line = yes_journal.inbound_payment_method_line_ids[:1]

                        payment_vals = {
                            'payment_type': 'inbound',
                            'partner_type': 'customer',
                            'journal_id': yes_journal.id,
                            'amount': amount,
                            'date': fields.Date.context_today(yes_journal),
                            'ref': f"YES Bank Incoming Ref: {bank_ref_id or api_ref_num or ''}",
                            'yes_bank_ref_id': bank_ref_id,
                            'yes_bank_api_ref': api_ref_num,
                            'yes_bank_status': 'completed' if txn_status == 'COMPLETED' else 'in_process',
                        }
                        if partner:
                            payment_vals['partner_id'] = partner.id
                        if pay_method_line:
                            payment_vals['payment_method_line_id'] = pay_method_line.id

                        new_payment = request.env['account.payment'].sudo().create(payment_vals)
                        new_payment.action_post()
                        _logger.info("Created and posted incoming payment %s for amount %s via callback", new_payment.name, amount)

            # Create log entry
            request.env['yes.bank.log'].sudo().create({
                'name': f"Callback ({tx_type})",
                'amount': signed_amount,
                'raw_data': json.dumps(data),
                'status': 'processed',
                'processed_date': fields.Datetime.now()
            })

            return {'status': 'success', 'message': 'Callback processed'}

        except Exception as e:
            _logger.error("Error in YES Bank Callback: %s", str(e))
            return {'status': 'error', 'message': str(e)}
