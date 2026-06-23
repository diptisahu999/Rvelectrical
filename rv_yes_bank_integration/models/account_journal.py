# -*- coding: utf-8 -*-
import requests
import json
import time
import os
import logging
# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    yes_bank_balance = fields.Float(string='YES Bank Balance', readonly=True)
    yes_bank_balance_date = fields.Datetime(string='Last Balance Update', readonly=True)

    def action_fetch_yes_bank_balance(self):
        self.ensure_one()
        
        # Get credentials
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('rv_yes_bank_integration.yes_bank_client_id')
        client_secret = get_param('rv_yes_bank_integration.yes_bank_client_secret')
        ftx_id = get_param('rv_yes_bank_integration.yes_bank_ftx_id')
        basic_auth_pass = get_param('rv_yes_bank_integration.yes_bank_basic_auth_password')
        cert_path = (get_param('rv_yes_bank_integration.yes_bank_cert_path') or '').strip()
        key_path = (get_param('rv_yes_bank_integration.yes_bank_key_path') or '').strip()
        account_number = get_param('rv_yes_bank_integration.yes_bank_account_number')
        cust_id = get_param('rv_yes_bank_integration.yes_bank_cust_id')
        env_mode = get_param('rv_yes_bank_integration.yes_bank_environment', 'uat')

        if not all([client_id, client_secret, ftx_id, basic_auth_pass, cert_path, key_path, account_number, cust_id]):
            raise UserError(_("Please complete YES Bank Integration settings in Accounting Configuration."))

        if not os.path.exists(cert_path):
            raise ValidationError(_("SSL Certificate file not found at: %s") % cert_path)
        if not os.path.exists(key_path):
            raise ValidationError(_("SSL Key file not found at: %s") % key_path)

        # Set API URL
        base_url = "https://skyway.yesbank.in/app/live" if env_mode == 'production' else "https://skyway.yesuat.bank.in/app/uat"
        url = f"{base_url}/APIBankingService/FTx/Payments/GetBalance"

        headers = {
            "Content-Type": "application/json",
            "X-IBM-Client-Id": client_id,
            "X-IBM-Client-Secret": client_secret,
            "FTxID": ftx_id
        }

        basic_auth = (ftx_id, basic_auth_pass)
        timestamp = str(int(time.time()))

        payload = {
            "ftxGetBalance": {
                "header": {
                    "version": "02.00",
                    "ftxID": ftx_id,
                    "custID": cust_id,
                    "acctNum": account_number,
                    "getBalanceRefNo": f"GB{timestamp}"
                }
            }
        }

        # Log request
        log_vals = {
            'name': 'Balance Inquiry Request',
            'amount': 0.0,
            'raw_data': f"URL: {url}\nHeaders: {json.dumps(headers)}\nPayload: {json.dumps(payload)}",
            'status': 'received'
        }
        log_record = self.env['yes.bank.log'].sudo().create(log_vals)

        try:
            _logger.info("Initiating YES Bank Balance Inquiry request...")
            response = requests.post(
                url,
                headers=headers,
                auth=basic_auth,
                cert=(cert_path, key_path),
                data=json.dumps(payload),
                timeout=15
            )

            # Update Log with Response
            log_record.write({
                'raw_data': log_record.raw_data + f"\n\nResponse Code: {response.status_code}\nResponse Body: {response.text}",
                'processed_date': fields.Datetime.now()
            })

            if response.status_code == 200:
                res_data = response.json()
                resp_obj = res_data.get('ftxGetBalanceResp', {})
                data_obj = resp_obj.get('data', {})
                clear_balance = data_obj.get('clearBalance')
                if clear_balance is not None:
                    balance_val = float(clear_balance)
                    self.write({
                        'yes_bank_balance': balance_val,
                        'yes_bank_balance_date': fields.Datetime.now()
                    })
                    log_record.write({'status': 'processed', 'amount': balance_val})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Success'),
                            'message': _('Live Balance fetched successfully: %s INR') % clear_balance,
                            'sticky': False,
                            'type': 'success',
                        }
                    }
                else:
                    log_record.write({'status': 'error'})
                    raise UserError(_("Unexpected response format from bank: %s") % response.text)
            else:
                log_record.write({'status': 'error'})
                raise UserError(_("Bank API Error (Status %s): %s") % (response.status_code, response.text))

        except Exception as e:
            log_record.write({
                'status': 'error',
                'raw_data': log_record.raw_data + f"\n\nConnection Exception: {str(e)}",
                'processed_date': fields.Datetime.now()
            })
            raise UserError(_("Failed to connect to YES Bank server: %s") % str(e))

    @api.model
    def cron_fetch_yes_bank_balance(self):
        # Search for all bank journals
        journals = self.search([('type', '=', 'bank')])
        account_number = self.env['ir.config_parameter'].sudo().get_param('rv_yes_bank_integration.yes_bank_account_number')
        
        for journal in journals:
            # Match the configured account number or look for "yes" in name/code
            is_yes_bank = False
            if account_number and (journal.bank_account_id.acc_number == account_number or journal.code == 'YES'):
                is_yes_bank = True
            elif 'yes' in (journal.name or '').lower():
                is_yes_bank = True
                
            if is_yes_bank:
                try:
                    journal.action_fetch_yes_bank_balance()
                except Exception as e:
                    _logger.error("Auto balance fetch failed for journal %s: %s", journal.name, str(e))
