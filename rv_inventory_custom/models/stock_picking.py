from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    rv_purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', help='Link to the Purchase Order')
    invoice_number = fields.Char(string="Invoice No.", compute='_compute_invoice_number', store=True)

    @api.depends('sale_id.invoice_ids.state', 'purchase_id.invoice_ids.state', 'sale_id.invoice_ids.name', 'purchase_id.invoice_ids.name')
    def _compute_invoice_number(self):
        for picking in self:
            invoices = self.env['account.move']
            if picking.sale_id:
                invoices = picking.sale_id.invoice_ids.filtered(lambda x: x.state != 'cancel')
            elif picking.purchase_id:
                invoices = picking.purchase_id.invoice_ids.filtered(lambda x: x.state != 'cancel')
            
            if invoices:
                 # Use mapped to get list of names, then join them. 
                 # Set helps remove duplicates if multiple lines point to same invoice? 
                 # Usually invoices are unique per order unless partial.
                 # Filter out False/Empty names (e.g. unposted invoices might have False name)
                 names = [n for n in invoices.mapped('name') if n]
                 picking.invoice_number = ", ".join(names)
            else:
                 picking.invoice_number = False

    def action_open_purchase_order(self):
        """
        Open a new Purchase Order form pre-filled with products from this picking.
        """
        self.ensure_one()
        
        # Prepare order lines
        order_lines = []
        for move in self.move_ids_without_package:
            if move.state not in ['done', 'cancel'] and move.product_id:
                # Basic logic: Add line for the remaining quantity
                # We use product_uom_qty (Demand) - quantity (Done)??
                # For simplified logic as requested ("click purchase button... open purchase form"),
                # we will pre-fill with the full demand of the line to be helpful.
                # The user can adjust qty in the PO form.
                
                qty_to_purchase = move.product_uom_qty
                
                order_lines.append((0, 0, {
                    'product_id': move.product_id.id,
                    'product_qty': qty_to_purchase,
                    'name': move.product_id.display_name,
                    'date_planned': fields.Date.today(),
                    'product_uom': move.product_uom.id,
                }))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Order',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_id': False,
            'target': 'current',
            'context': {
                'default_order_line': order_lines,
                'default_origin': self.name,
                # Link back to this picking if we want? 
                # 'default_picking_type_id': ... (incoming shipment)
            }
        }
