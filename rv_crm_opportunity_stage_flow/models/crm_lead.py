from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = "crm.lead"

    manual_last_update = fields.Datetime(
        string="Last Update Date",
        related='write_date',
        store=False,
        readonly=True
    )