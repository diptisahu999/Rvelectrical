# models/stock_overview.py
from odoo import models, fields, api

class StockOverview(models.Model):
    _name = 'rv.stock.overview'
    _description = 'Stock Overview'

    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade')

    on_hand_qty = fields.Float(string='On Hand', compute='_compute_stock', store=False)
    incoming_qty = fields.Float(string='Incoming', compute='_compute_stock', store=False)
    reserved_qty = fields.Float(string='Reserved', compute='_compute_stock', store=False)
    forecasted_qty = fields.Float(string='Forecasted', compute='_compute_stock', store=False)

    @api.depends('product_id')
    def _compute_stock(self):
        for rec in self:
            template = rec.product_id
            variants = template.product_variant_ids

            rec.on_hand_qty = sum(variants.mapped('qty_available'))
            rec.incoming_qty = sum(variants.mapped('incoming_qty'))
            rec.reserved_qty = sum(variants.mapped('outgoing_qty'))
            rec.forecasted_qty = sum(variants.mapped('virtual_available'))


    @api.model
    def init(self):
        products = self.env['product.template'].search([
            ('type', 'in', ['consu', 'combo'])
        ])
        existing = self.search([]).mapped('product_id').ids

        for product in products:
            if product.id not in existing:
                self.create({'product_id': product.id})
