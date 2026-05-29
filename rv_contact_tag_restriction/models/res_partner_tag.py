from odoo import models, _
from odoo.exceptions import UserError

class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    def create(self, vals):
        if not self.env.user.has_group(
            'rv_contact_tag_restriction.group_contact_tag_create'
        ):
            raise UserError(
                _("You are not allowed to create Contact Tags.")
            )
        return super().create(vals)
