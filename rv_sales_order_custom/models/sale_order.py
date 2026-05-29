from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_invoice_direct(self):
        """
        Always create a NEW regular invoice in draft state.
        No wizard. Supports multiple SO.
        """
        self.ensure_one()  # optional: remove if you want multi-SO

        invoices = self._create_invoices(final=False)

        # Open last created invoice (UX friendly)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoices.id,
            'target': 'current',
        }
