from odoo import api, fields, models
from num2words import num2words


class SaleOrder(models.Model):
    _inherit = "sale.order"

    terms_condition_id = fields.Many2one("terms.and.conditions", "Terms and Condition")
    additional_notes = fields.Html(string="Additional Notes")
    amount_total_words = fields.Char(
        string='Total (In Words)',
        compute='_compute_amount_total_words'
    )
    # global_discount = fields.Float(
    #     string='Discount (%)',
    #     digits='Discount',
    #     default=0.0
    # )
    # discount_amount = fields.Monetary(
    #     string='Discount Amount',
    #     compute='_compute_discount_amount',
    #     store=True
    # )
    # price_after_discount = fields.Monetary(
    #     string='Price After Discount',
    #     compute='_compute_price_after_discount',
    #     store=True
    # )
    delivery_count = fields.Integer(
        string='Delivery Orders',
        compute='_compute_delivery_count',
        store=False  # Changed to store=False since we can't depend on picking_ids
    )

    def _compute_delivery_count(self):
        """Compute delivery count, handling case where sale_stock isn't installed"""
        for order in self:
            if hasattr(order, 'picking_ids'):
                order.delivery_count = len(order.picking_ids)
            else:
                order.delivery_count = 0

    # @api.depends('amount_total', 'global_discount')
    # def _compute_discount_amount(self):
    #     for order in self:
    #         order.discount_amount = order.amount_total * (order.global_discount / 100.0)
    #
    # @api.depends('amount_total', 'discount_amount')
    # def _compute_price_after_discount(self):
    #     for order in self:
    #         order.price_after_discount = order.amount_total - order.discount_amount

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for record in self:
            try:
                record.amount_total_words = num2words(record.amount_total, lang='en').title()
            except:
                record.amount_total_words = ''

    @api.onchange("terms_condition_id")
    def _onchange_terms_condition_id(self):
        if self.terms_condition_id:
            self.note = self.terms_condition_id.terms_condition

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        # invoice_vals ['global_discount']=self.global_discount
        return invoice_vals