from odoo import models, fields

class SalesTarget(models.Model):
    _name = 'sales.target'
    _description = 'Sales Target'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        readonly=True
    )

    line_ids = fields.One2many(
        'sales.target.line',
        'target_id',
        string='Target Lines'
    )



class SalesTargetLine(models.Model):
    _name = 'sales.target.line'
    _description = 'Sales Target Line'

    target_id = fields.Many2one(
        'sales.target',
        string='Sales Target',
        ondelete='cascade'
    )

    target_amount = fields.Float(
        string='Target Amount',
        required=True
    )

    month = fields.Selection(
        selection=[
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')
        ],
        string='Month',
        required=True
    )

    year = fields.Selection(
        [(str(y), str(y)) for y in range(2024, 2035)],
        string='Year',
        required=True,
        default=lambda self: str(fields.Date.today().year)
    )

    assigned_date = fields.Date(
        string='Assigned Date',
        default=fields.Date.context_today,
        readonly=True
    )
