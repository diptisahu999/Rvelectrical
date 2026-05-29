# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MrpBomLine(models.Model):
    """
    Model for representing BoM lines with additional fields and methods for
    product configuration.
    Inherits from 'mrp.bom.line' model.
    """
    _inherit = 'mrp.bom.line'

    configuration_template_id = fields.Many2one(
        'product.template', 'Product Template',
        check_company=True, required=False,
        help="Select a product template to use the configurator.")
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value',
        inverse_name='mrp_bom_line_id',
        string="Custom Values",
        help="product custom attribute values",
        store=True, readonly=False, copy=True)
    product_config_mode = fields.Selection(
        related='configuration_template_id.product_config_mode',
        depends=['configuration_template_id'],
        help="product configuration mode")

    @api.onchange('configuration_template_id')
    def on_change_configuration_template_id(self):
        """ Returns a client action to open the product configurator dialog.
        """
        if not self.configuration_template_id:
            return {}
        
        # Check if configurator is needed
        res = self.configuration_template_id.get_single_product_variant()
        if res.get('product_id'):
            self.product_id = res['product_id']
            return {}
            
        return {
            'type': 'ir.actions.client',
            'tag': 'mrp_bom_configurator',
            'params': {
                'product_template_id': self.configuration_template_id.id,
                'quantity': self.product_qty or 1.0,
                'product_uom_id': self.product_uom_id.id,
                'context': self.env.context,
            }
        }

    def action_open_configurator(self):
        """ Manual button trigger for configurator.
        """
        return self.on_change_configuration_template_id()

