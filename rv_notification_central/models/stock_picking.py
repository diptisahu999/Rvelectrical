from odoo import models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        # Ensure we only notify if validation was successful and record is done
        for picking in self.filtered(lambda p: p.state == 'done'):
            if picking.picking_type_code == 'outgoing':
                self.env['push.service'].sudo().notify_event(
                    event_code='delivery_dispatch',
                    record=picking,
                    title=_("Delivery Dispatched"),
                    body=_("Transfer: %s\nCustomer: %s\nSource: %s") % (
                        picking.name,
                        picking.partner_id.name or _("N/A"),
                        picking.origin or _("N/A")
                    )
                )
            elif picking.picking_type_code == 'incoming':
                self.env['push.service'].sudo().notify_event(
                    event_code='product_receive',
                    record=picking,
                    title=_("Product Received"),
                    body=_("Transfer: %s\nVendor: %s\nSource: %s") % (
                        picking.name,
                        picking.partner_id.name or _("N/A"),
                        picking.origin or _("N/A")
                    )
                )
        return res
