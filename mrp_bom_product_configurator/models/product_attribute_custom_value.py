# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductAttributeCustomValue(models.Model):
    """
    Model for representing custom attribute values for a BoM line.
    Inherits from 'product.attribute.custom.value' model.
    """
    _inherit = "product.attribute.custom.value"

    mrp_bom_line_id = fields.Many2one('mrp.bom.line',
                                      string="BoM Line",
                                      required=False, ondelete='cascade',
                                      help="BoM lines")
