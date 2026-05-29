from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    terms_condition_id = fields.Many2one("terms.and.conditions", "Terms and Condition")

    @api.onchange("terms_condition_id")
    def _onchange_terms_condition_id(self):
        if self.terms_condition_id:
            self.notes = self.terms_condition_id.terms_condition
