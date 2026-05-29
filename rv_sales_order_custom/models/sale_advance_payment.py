# from odoo import models, api

# class SaleAdvancePaymentInv(models.TransientModel):
#     _inherit = 'sale.advance.payment.inv'

#     @api.model
#     def default_get(self, fields):
#         res = super().default_get(fields)
#         # Force Regular Invoice always
#         res['advance_payment_method'] = 'delivered'
#         return res

#     @api.onchange('advance_payment_method')
#     def _force_regular_invoice(self):
#         self.advance_payment_method = 'delivered'

