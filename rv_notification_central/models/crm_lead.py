from odoo import api, models, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            self.env['push.service'].sudo().notify_event(
                event_code='crm_lead_create',
                record=lead,
                title=_("New Lead Created"),
                body=_("Lead: %s\nCustomer: %s") % (
                    lead.name,
                    lead.partner_name or lead.partner_id.name or _("N/A")
                )
            )
        return leads
