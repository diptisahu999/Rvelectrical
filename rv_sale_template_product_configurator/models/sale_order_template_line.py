from odoo import api, fields, models

class SaleOrderTemplateLine(models.Model):
    _inherit = 'sale.order.template.line'

    configuration_template_id = fields.Many2one(
        'product.template', 'Product',
        check_company=True, required=False,
        help="Select a product to use the configurator.")
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value',
        inverse_name='sale_order_template_line_id',
        string="Custom Values",
        help="product custom attribute values",
        store=True, readonly=False, copy=True)
    product_config_mode = fields.Selection(
        related='configuration_template_id.product_config_mode',
        depends=['configuration_template_id'],
        help="product configuration mode")

    @api.onchange('product_id')
    def _onchange_product_id_set_template(self):
        if self.product_id:
            self.configuration_template_id = self.product_id.product_tmpl_id

    @api.onchange('configuration_template_id')
    def on_change_configuration_template_id(self):
        """ Returns a client action to open the product configurator dialog. """
        if not self.configuration_template_id:
            return {}
        
        # Check if configurator is needed
        res = self.configuration_template_id.get_single_product_variant()
        if res.get('product_id'):
            self.product_id = res['product_id']
            return {}
            
        return {
            'type': 'ir.actions.client',
            'tag': 'mrp_bom_configurator', # We can likely reuse the name if we want, or define our own. 
            # But the tag is usually linked to a JS backend action. 
            # In the mrp_bom module, it returns tag 'mrp_bom_configurator'.
            'params': {
                'product_template_id': self.configuration_template_id.id,
                'quantity': self.product_uom_qty or 1.0,
                'product_uom_id': self.product_uom_id.id,
                'context': self.env.context,
            }
        }

    def action_open_configurator(self):
        """ Manual button trigger for configurator. """
        return self.on_change_configuration_template_id()
