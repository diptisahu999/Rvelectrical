from odoo import models, api, _
from odoo.exceptions import UserError, AccessError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def unlink(self):
        if not (self.env.user.has_group('rv_app_access.group_purchase_delete') or self.env.user.has_group('purchase.group_purchase_manager')):
            raise AccessError(_("You are not allowed to delete Purchase entries."))
        return super(PurchaseOrder, self).unlink()
