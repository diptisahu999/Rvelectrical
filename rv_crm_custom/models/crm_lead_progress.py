from odoo import models, fields, api
import math

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    followup_progress = fields.Float(
        string='Progress',
        compute='_compute_followup_progress',
        store=False,
        help='Calculates progress based on follow ups.'
    )

    def _compute_followup_progress(self):
        for lead in self:
            domain = [('lead_id', '=', lead.id)]
            if lead.type == 'opportunity':
                 domain.append(('state', '=', 'done'))
            
            count = self.env['crm.lead.followup'].search_count(domain)

            progress = min((count / 6) * 100, 100)
            lead.followup_progress = round(progress, 2)
