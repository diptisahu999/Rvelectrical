from odoo import models, api, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        for order in self:
            # Check if partner is a company and has no GST number (vat)
            if order.partner_id.company_type == 'company' and not order.partner_id.vat:
                raise ValidationError(_("Please add GST number for company contact: %s") % order.partner_id.name)
        
        return super(SaleOrder, self).action_confirm()

    @api.onchange('partner_id')
    def _onchange_partner_id_reset_shipping(self):
        """
        When the customer changes, reset the delivery address if it no longer
        belongs to the newly selected customer (i.e. it is from a different contact).
        """
        if self.partner_id and self.partner_shipping_id:
            valid_ids = (
                self.partner_id
                | self.partner_id.child_ids.filtered(
                    lambda c: c.type == 'delivery'
                )
            ).ids
            if self.partner_shipping_id.id not in valid_ids:
                self.partner_shipping_id = self.partner_id
