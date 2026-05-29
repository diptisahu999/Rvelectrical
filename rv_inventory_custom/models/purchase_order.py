from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rv_custom_picking_ids = fields.One2many(
        'stock.picking', 
        'rv_purchase_order_id', 
        string='Custom Linked Pickings'
    )

    @api.depends('order_line.move_ids.picking_id', 'rv_custom_picking_ids')
    def _compute_picking_ids(self):
        super(PurchaseOrder, self)._compute_picking_ids()
        for order in self:
            # Union of standard pickings and custom linked pickings
            order.picking_ids = order.picking_ids | order.rv_custom_picking_ids

    def action_view_picking(self):
        """
        Override to ensure custom pickings are included in the action.
        """
        # Call super to get the basic action structure
        action = super(PurchaseOrder, self).action_view_picking()
        
        # Ensure we are using the full set of picking_ids (which now includes custom ones)
        # We explicitly rebuild the domain to be safe, as some versions might build it differently.
        if self.picking_ids:
            action['domain'] = [('id', 'in', self.picking_ids.ids)]
            action['context'] = {'default_rv_purchase_order_id': self.id} # Optional: ease creation
        
        return action
