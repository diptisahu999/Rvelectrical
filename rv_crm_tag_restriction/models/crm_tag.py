from odoo import models, api, _
from odoo.exceptions import AccessError

class CrmTag(models.Model):
    _inherit = "crm.tag"

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
            "rv_crm_tag_restriction.group_crm_tag_creator"
        ):
            raise AccessError(
                _("You are not allowed to create CRM Tags.")
            )
        return super().create(vals_list)
