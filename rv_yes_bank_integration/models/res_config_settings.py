# -*- coding: utf-8 -*-
# pyrefly: ignore [missing-import]
from odoo import models, fields, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

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
    yes_bank_otp_email = fields.Char(
        string='YES Bank Secure OTP Email',
        config_parameter='rv_yes_bank_integration.yes_bank_otp_email',
        help="All transaction OTP authorization codes will be sent exclusively to this email address."
    )

    def action_test_otp_email(self):
        self.ensure_one()
        otp_email = self.yes_bank_otp_email
        if not otp_email:
            raise UserError(_("Please configure the Secure OTP Email address first."))
            
        get_param = self.env['ir.config_parameter'].sudo().get_param
        mail_server = self.env['ir.mail_server'].sudo().search([], limit=1)
        email_from = mail_server.smtp_user or get_param('mail.default.from') or self.env.user.email
        
        mail_values = {
            'subject': _('YES Bank Integration: Test Email Delivery'),
            'email_from': email_from,
            'email_to': otp_email,
            'body_html': _('<p>This is a test email from Odoo to verify your YES Bank OTP delivery configuration.</p>')
        }
        
        try:
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send(raise_exception=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Test email sent successfully to %s. Please check your inbox.') % otp_email,
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(_("Email delivery failed: %s\n\nThis indicates Odoo's Outgoing Mail Server is not configured correctly or is rejecting the email relay.") % str(e))

