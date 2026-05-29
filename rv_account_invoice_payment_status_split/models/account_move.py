from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_status_group = fields.Selection(
        [
            ("draft", "Draft"),
            ("cancel", "Cancelled"),
            ("not_paid", "Not Paid"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("reversed", "Reversed"),
            ("blocked", "Blocked"),
        ],
        compute="_compute_payment_status_group",
        store=True,
    )

    @api.depends("state", "payment_state", "move_type")
    def _compute_payment_status_group(self):
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                move.payment_status_group = False
                continue

            if move.state == "draft":
                move.payment_status_group = "draft"
            elif move.state == "cancel":
                move.payment_status_group = "cancel"
            else:
                move.payment_status_group = move.payment_state
