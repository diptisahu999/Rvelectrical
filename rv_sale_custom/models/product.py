# pyrefly: ignore [missing-import]
from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_additional_product = fields.Boolean(
        string="Is Additional Product",
        default=False,
        help="If checked, this product can only be selected as an additional charge in sales orders."
    )
