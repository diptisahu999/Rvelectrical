from odoo import models, fields

class PushLog(models.Model):
    _name = 'push.notification.log'
    _description = 'Push Notification Log'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string='User', required=True)
    title = fields.Char(string='Title')
    body = fields.Text(string='Body')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('no_device', 'No Device Registered'),
        ('invalid_token', 'Invalid Token (Unlinked)')
    ], string='Status', required=True)
    firebase_id = fields.Char(string='Firebase Message ID')
    error_message = fields.Text(string='Error Message')
    data_payload = fields.Text(string='Data Payload')
