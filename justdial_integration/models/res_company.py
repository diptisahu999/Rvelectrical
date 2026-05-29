from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    justdial_salesperson_id = fields.Many2one(
        'res.users',
        string="Justdial Salesperson"
    )

    