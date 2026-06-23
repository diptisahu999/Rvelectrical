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

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    yes_bank_ref_id = fields.Char(string='YES Bank Ref ID', readonly=True, copy=False)
    yes_bank_api_ref = fields.Char(string='YES Bank API Ref', readonly=True, copy=False)
    yes_bank_status = fields.Selection([
        ('draft', 'Not Sent'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='YES Bank Status', default='draft', readonly=True, copy=False)

    yes_bank_payment_type = fields.Selection([
        ('IMPS', 'IMPS'),
        ('NEFT', 'NEFT'),
        ('RTGS', 'RTGS')
    ], string='YES Bank Payment Mode', default='IMPS', copy=False)

    def action_send_to_yes_bank(self):
        self.ensure_one()
        if self.payment_type != 'outgoing':
            raise UserError(_("Only outgoing payments can be sent to YES Bank."))
        if self.state != 'posted':
            raise UserError(_("Only confirmed (posted) payments can be sent to YES Bank."))
        if self.yes_bank_status in ('in_process', 'completed'):
            raise UserError(_("This payment has already been sent to YES Bank (Status: %s).") % self.yes_bank_status)

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

        if not self.partner_bank_id:
            raise UserError(_("Please select a recipient bank account for this payment."))

        bene_acc = self.partner_bank_id.acc_number
        bene_ifsc = self.partner_bank_id.bank_id.bic or getattr(self.partner_bank_id, 'bank_bic', False)
        if not bene_acc or not bene_ifsc:
            raise UserError(_("Recipient bank account number or IFSC code is missing."))

        # Set API URL
        base_url = "https://skyway.yesbank.in/app/live" if env_mode == 'production' else "https://skyway.yesuat.bank.in/app/uat"
        url = f"{base_url}/APIBankingService/FTx/Payments/PayReq"

        headers = {
            "Content-Type": "application/json",
            "X-IBM-Client-Id": client_id,
            "X-IBM-Client-Secret": client_secret,
            "FTxID": ftx_id
        }

        basic_auth = (ftx_id, basic_auth_pass)
        timestamp = str(int(time.time()))
        api_ref = f"FTXH{timestamp}"
        cust_ref = str(self.id)

        payload = {
            "ftxPayReq": {
                "header": {
                    "version": "01.00",
                    "ftxID": ftx_id,
                    "channel": "API",
                    "custID": cust_id,
                    "partnerCode": ftx_id,
                    "txnType": "NOD",
                    "pymtType": self.yes_bank_payment_type or "IMPS"
                },
                "payload": {
                    "common": {
                        "apiRefNum": api_ref,
                        "custRefNum": cust_ref,
                        "valueDt": fields.Date.today().strftime('%d-%m-%Y'),
                        "currencyCd": "INR",
                        "currencyRate": "1.00",
                        "amount": f"{self.amount:.2f}",
                        "purposeCd": "MER",
                        "purposeCdRef": "",
                        "remarks": self.memo or "Vendor Payment",
                        "debitNarration": "YESBANK"
                    },
                    "remitBlk": {
                        "rmtrAcctNum": account_number,
                        "rmtrName": self.company_id.name or "R V Enterprise"
                    },
                    "beneBlk": {
                        "beneCode": f"BENE{timestamp}",
                        "beneName": self.partner_id.name,
                        "beneIFSC": bene_ifsc,
                        "beneAcctNum": bene_acc
                    }
                }
            }
        }

        # Log request
        log_record = self.env['yes.bank.log'].sudo().create({
            'name': f'Payment Request {self.name}',
            'amount': -self.amount,
            'raw_data': f"URL: {url}\nHeaders: {json.dumps(headers)}\nPayload: {json.dumps(payload)}",
            'status': 'received'
        })

        try:
            _logger.info("Initiating YES Bank Payment request...")
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
                resp_obj = res_data.get('ftxPayResp', {})
                data_obj = resp_obj.get('data', {})
                bank_ref = data_obj.get('bankRefId')
                status = data_obj.get('txnStatus')

                if bank_ref:
                    status_mapping = {
                        'IN_PROCESS': 'in_process',
                        'COMPLETED': 'completed',
                        'FAILED': 'failed'
                    }
                    mapped_status = status_mapping.get(status, 'in_process')
                    self.write({
                        'yes_bank_ref_id': bank_ref,
                        'yes_bank_api_ref': api_ref,
                        'yes_bank_status': mapped_status
                    })
                    log_record.write({'status': 'processed'})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Payment Sent'),
                            'message': _('Payment has been dispatched. Status: %s. Bank Ref: %s') % (status, bank_ref),
                            'sticky': False,
                            'type': 'success',
                        }
                    }
                else:
                    log_record.write({'status': 'error'})
                    raise UserError(_("No bank reference returned by YES Bank. Response: %s") % response.text)
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

    def action_check_yes_bank_status(self):
        self.ensure_one()
        if not self.yes_bank_ref_id:
            raise UserError(_("This payment has no YES Bank Reference ID. Send the payment first."))

        # Get credentials
        get_param = self.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('rv_yes_bank_integration.yes_bank_client_id')
        client_secret = get_param('rv_yes_bank_integration.yes_bank_client_secret')
        ftx_id = get_param('rv_yes_bank_integration.yes_bank_ftx_id')
        basic_auth_pass = get_param('rv_yes_bank_integration.yes_bank_basic_auth_password')
        cert_path = (get_param('rv_yes_bank_integration.yes_bank_cert_path') or '').strip()
        key_path = (get_param('rv_yes_bank_integration.yes_bank_key_path') or '').strip()
        cust_id = get_param('rv_yes_bank_integration.yes_bank_cust_id')
        env_mode = get_param('rv_yes_bank_integration.yes_bank_environment', 'uat')

        if not all([client_id, client_secret, ftx_id, basic_auth_pass, cert_path, key_path, cust_id]):
            raise UserError(_("Please complete YES Bank Integration settings in Accounting Configuration."))

        # Set API URL
        base_url = "https://skyway.yesbank.in/app/live" if env_mode == 'production' else "https://skyway.yesuat.bank.in/app/uat"
        url = f"{base_url}/APIBankingService/FTx/Payments/GetStatus"

        headers = {
            "Content-Type": "application/json",
            "X-IBM-Client-Id": client_id,
            "X-IBM-Client-Secret": client_secret,
            "FTxID": ftx_id
        }

        basic_auth = (ftx_id, basic_auth_pass)
        timestamp = str(int(time.time()))

        payload = {
            "ftxGetStatus": {
                "header": {
                    "version": "02.00",
                    "ftxID": ftx_id,
                    "custID": cust_id,
                    "getStatusRefNo": f"G{timestamp}"
                },
                "payload": {
                    "bankRefId": self.yes_bank_ref_id
                }
            }
        }

        log_record = self.env['yes.bank.log'].sudo().create({
            'name': f'Status Check for {self.name}',
            'amount': 0.0,
            'raw_data': f"URL: {url}\nHeaders: {json.dumps(headers)}\nPayload: {json.dumps(payload)}",
            'status': 'received'
        })

        try:
            _logger.info("Checking status of YES Bank payment...")
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
                resp_obj = res_data.get('ftxGetStatusResp', {})
                data_obj = resp_obj.get('data', {})
                status = data_obj.get('txnStatus')

                if status:
                    status_mapping = {
                        'IN_PROCESS': 'in_process',
                        'COMPLETED': 'completed',
                        'FAILED': 'failed'
                    }
                    mapped_status = status_mapping.get(status, 'in_process')
                    self.write({'yes_bank_status': mapped_status})
                    log_record.write({'status': 'processed'})
                    
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Status Updated'),
                            'message': _('Current transaction status is: %s') % status,
                            'sticky': False,
                            'type': 'info',
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
