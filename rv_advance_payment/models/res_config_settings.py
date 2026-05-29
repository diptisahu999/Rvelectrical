from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_sale_advance_payment = fields.Boolean(
        string="Allow Sale Order Advance Payment",
        config_parameter='rv_advance_payment.allow_sale_advance_payment'
    )
    allow_purchase_advance_payment = fields.Boolean(
        string="Allow Purchase Order Advance Payment",
        config_parameter='rv_advance_payment.allow_purchase_advance_payment'
    )
