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
