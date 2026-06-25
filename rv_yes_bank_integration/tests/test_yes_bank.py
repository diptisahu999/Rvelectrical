# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock

class TestYesBankIntegration(TransactionCase):

    def setUp(self):
        super(TestYesBankIntegration, self).setUp()
        
        # Set config parameters
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_client_id', 'test_client_id')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_client_secret', 'test_client_secret')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_ftx_id', 'test_ftx_id')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_basic_auth_password', 'test_pwd')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_cert_path', __file__) 
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_key_path', __file__) 
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_account_number', '1234567890')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_cust_id', '9876543')
        self.env['ir.config_parameter'].sudo().set_param('rv_yes_bank_integration.yes_bank_environment', 'uat')

        # Create a test bank journal
        self.journal = self.env['account.journal'].create({
            'name': 'Test YES Bank',
            'code': 'TYBL',
            'type': 'bank',
        })

    @patch('requests.post')
    def test_fetch_balance_success(self, mock_post):
        # Mock successful balance response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ftxGetBalanceResp": {
                "version": "02.00",
                "data": {
                    "balFetchTimeStamp": "07-01-2026 16:13:45.045",
                    "clearBalance": "50000.50"
                }
            }
        }
        mock_post.return_value = mock_response

        # Fetch balance
        self.journal.action_fetch_yes_bank_balance()

        # Check balance updated
        self.assertEqual(self.journal.yes_bank_balance, 50000.50)
        
        # Check that request log was created
        log = self.env['yes.bank.log'].search([('name', '=', 'Balance Inquiry Request')], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.status, 'processed')
        self.assertEqual(log.amount, 50000.50)

    @patch('odoo.http.request')
    def test_callback_credit_incoming(self, mock_request):
        mock_request.env = self.env
        # pyrefly: ignore [missing-import]
        from odoo.addons.rv_yes_bank_integration.controllers.main import YesBankCallback
        
        callback_data = {
            "ftxPayCallback": {
                "version": "1.0",
                "data": {
                    "bankRefId": "YESBRCREDIT123",
                    "amount": "15000.00",
                    "txnStatus": "COMPLETED",
                    "beneAcctNum": "1234567890", # Matches company acct
                    "beneName": "Test Customer",
                }
            }
        }
        
        # Instantiate controller and process callback
        controller = YesBankCallback()
        response = controller._process_callback(callback_data)
        
        self.assertEqual(response.get('status'), 'success')
        
        # Check yes.bank.log
        log = self.env['yes.bank.log'].search([('name', '=', 'Callback (CREDIT)')], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.amount, 15000.00)
        self.assertEqual(log.status, 'processed')
        
        # Check created account.payment
        payment = self.env['account.payment'].search([
            ('payment_type', '=', 'inbound'),
            ('yes_bank_ref_id', '=', 'YESBRCREDIT123')
        ], limit=1)
        self.assertTrue(payment)
        self.assertEqual(payment.amount, 15000.00)
        self.assertEqual(payment.state, 'posted')

    @patch('odoo.http.request')
    def test_callback_debit_outgoing(self, mock_request):
        mock_request.env = self.env
        # pyrefly: ignore [missing-import]
        from odoo.addons.rv_yes_bank_integration.controllers.main import YesBankCallback
        
        # Create partner
        partner = self.env['res.partner'].create({'name': 'Test Vendor'})
        partner_bank = self.env['res.partner.bank'].create({
            'acc_number': '9876543210',
            'partner_id': partner.id,
            'bank_id': self.env['res.bank'].create({'name': 'HDFC', 'bic': 'HDFC0004024'}).id
        })
        
        # Create outbound payment in Odoo
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': 25000.00,
            'journal_id': self.journal.id,
            'partner_bank_id': partner_bank.id,
        })
        # Mock posting it (or set status directly since it's outbound)
        payment.action_post()
        
        callback_data = {
            "ftxPayCallback": {
                "version": "1.0",
                "data": {
                    "bankRefId": "YESBRDEBIT123",
                    "custRefNum": str(payment.id),
                    "amount": "25000.00",
                    "txnStatus": "COMPLETED"
                }
            }
        }
        
        controller = YesBankCallback()
        response = controller._process_callback(callback_data)
        
        self.assertEqual(response.get('status'), 'success')
        self.assertEqual(payment.yes_bank_status, 'completed')
        
        log = self.env['yes.bank.log'].search([('name', '=', 'Callback (DEBIT)')], limit=1)
        self.assertTrue(log)
        self.assertEqual(log.amount, -25000.00)

