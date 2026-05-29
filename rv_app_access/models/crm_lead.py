from odoo import models, api, _
from odoo.exceptions import AccessError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def unlink(self):
        if not (self.env.user.has_group('rv_app_access.group_sales_crm_delete') or self.env.user.has_group('sales_team.group_sale_manager')):
            raise AccessError(_("You are not allowed to delete CRM entries."))
        return super(CrmLead, self).unlink()
