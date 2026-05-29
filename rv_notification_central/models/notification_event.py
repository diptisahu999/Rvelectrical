from odoo import fields, models

class NotificationEvent(models.Model):
    _name = 'push.notification.event'
    _description = 'Push Notification Event'
    _order = 'sequence, id'

    name = fields.Char(string='Event Name', required=True)
    code = fields.Char(string='Event Code', required=True, index=True)
    sequence = fields.Integer(default=10)
    is_active = fields.Boolean(string='Active', default=True)
    
    # primary_user_id = fields.Many2one(
    #     'res.users',
    #     string='Primary User (User 1)',
    #     help="Specific primary user for this event."
    # )

    secondary_user_ids = fields.Many2many(
        'res.users',
        'notification_event_secondary_rel',
        'event_id',
        'user_id',
        string='Supervisors',
        help="Specific users (Managers/Admins) to notify for this event."
    )

    monitored_user_ids = fields.Many2many(
        'res.users',
        'notification_event_user_rel',
        'event_id',
        'user_id',
        string='Team Members',
        help="The Supervisors will ONLY be notified if the action is performed by one of these users. Leave empty for all users."
    )
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The event code must be unique!')
    ]
