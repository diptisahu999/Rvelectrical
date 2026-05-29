from odoo import models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            self.env['push.service'].sudo().notify_event(
                event_code='sale_order_confirm',
                record=order,
                title=_("Sale Order Confirmed"),
                body=_("Order: %s\nCustomer: %s\nTotal: %s") % (
                    order.name,
                    order.partner_id.name,
                    order.amount_total
                )
            )
        return res
