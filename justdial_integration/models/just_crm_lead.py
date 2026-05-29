from odoo import fields, models

class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    is_justdial = fields.Boolean("Justdial")
    justdial_lead_id = fields.Char("Justdial Lead ID")

    def assign_justdial_leads(self):
        company = self.env.company
        user = company.justdial_salesperson_id

        if not user:
            cron_ref = self.env.ref('justdial_integration.stpl_justdial_connector_cron', raise_if_not_found=False)
            user = cron_ref.user_id if cron_ref else self.env.ref('base.user_admin')

        # Find unassigned Justdial leads
        leads = self.search([
            ('is_justdial', '=', True),
            ('user_id', '=', False)
        ])

        for lead in leads:
            lead.user_id = user.id

    #update DB is_justdial = true (for old lead)
    def init(self):
        """Auto run on module install/upgrade"""

        self.env.cr.execute("""
            UPDATE crm_lead
            SET is_justdial = TRUE
            WHERE source_id IN (
                SELECT id FROM utm_source WHERE name = 'Justdial'
            )
            AND (is_justdial IS NULL OR is_justdial = FALSE)
        """)
