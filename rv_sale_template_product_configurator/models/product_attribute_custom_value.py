from odoo import fields, models

class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_template_line_id = fields.Many2one(
        'sale.order.template.line',
        string="Sale Order Template Line",
        required=False, ondelete='cascade',
        help="Sale Order Template lines")
