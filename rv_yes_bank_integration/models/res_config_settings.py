# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    yes_bank_client_id = fields.Char(
        string='YES Bank Client ID (API Key)',
        config_parameter='rv_yes_bank_integration.yes_bank_client_id'
    )
    yes_bank_client_secret = fields.Char(
        string='YES Bank Client Secret (API Secret)',
        config_parameter='rv_yes_bank_integration.yes_bank_client_secret'
    )
    yes_bank_ftx_id = fields.Char(
        string='YES Bank FTX ID',
        config_parameter='rv_yes_bank_integration.yes_bank_ftx_id'
    )
    yes_bank_basic_auth_password = fields.Char(
        string='YES Bank Basic Auth Password',
        config_parameter='rv_yes_bank_integration.yes_bank_basic_auth_password'
    )
    yes_bank_cert_path = fields.Char(
        string='SSL Certificate File Path (.crt)',
        config_parameter='rv_yes_bank_integration.yes_bank_cert_path'
    )
    yes_bank_key_path = fields.Char(
        string='SSL Key File Path (.key)',
        config_parameter='rv_yes_bank_integration.yes_bank_key_path'
    )
    yes_bank_account_number = fields.Char(
        string='YES Bank Account Number',
        config_parameter='rv_yes_bank_integration.yes_bank_account_number'
    )
    yes_bank_cust_id = fields.Char(
        string='YES Bank Customer ID',
        config_parameter='rv_yes_bank_integration.yes_bank_cust_id'
    )
    yes_bank_environment = fields.Selection([
        ('uat', 'UAT / Testing'),
        ('production', 'Production')
    ], string='YES Bank Environment', default='uat', config_parameter='rv_yes_bank_integration.yes_bank_environment')
