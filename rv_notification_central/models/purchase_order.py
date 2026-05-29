from odoo import models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            self.env['push.service'].sudo().notify_event(
                event_code='purchase_order_confirm',
                record=order,
                title=_("Purchase Order Confirmed"),
                body=_("Order: %s\nVendor: %s\nTotal: %s") % (
                    order.name,
                    order.partner_id.name,
                    order.amount_total
                )
            )
        return res
