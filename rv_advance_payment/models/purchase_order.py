from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    advance_payment_ids = fields.One2many(
        'account.payment', 'purchase_order_id', string='Advance Payments'
    )
    advance_payment_count = fields.Integer(compute='_compute_advance_payment_count', string='Advance Payments Count')
    is_fully_paid_via_advance = fields.Boolean(compute='_compute_is_fully_paid_via_advance', string='Is Fully Paid via Advance')
    remaining_amount = fields.Monetary(string="Remaining Amount", compute='_compute_remaining_amount', store=True, currency_field='currency_id')

    @api.depends('amount_total', 'advance_payment_ids.amount', 'advance_payment_ids.state')
    def _compute_remaining_amount(self):
        for order in self:
            total_advance = sum(order.advance_payment_ids.filtered(lambda p: p.state != 'cancel').mapped('amount'))
            order.remaining_amount = order.amount_total - total_advance

    @api.depends('advance_payment_ids.amount', 'advance_payment_ids.state', 'amount_total')
    def _compute_is_fully_paid_via_advance(self):
        for order in self:
            total_advance = sum(order.advance_payment_ids.filtered(lambda p: p.state != 'cancel').mapped('amount'))
            # Only consider it properly 'fully paid via advance' if amount is > 0
            # If amount is 0, we treat it as NOT fully paid to keep the button visible (e.g. for deposits or initial testing)
            order.is_fully_paid_via_advance = order.amount_total > 0 and total_advance >= order.amount_total

    @api.depends('advance_payment_ids')
    def _compute_advance_payment_count(self):
        for order in self:
            order.advance_payment_count = len(order.advance_payment_ids)

    def action_register_advance_payment(self):
        self.ensure_one()
        if not self.env['ir.config_parameter'].sudo().get_param('rv_advance_payment.allow_purchase_advance_payment'):
             raise UserError(_("Advance Payment for Purchase Orders is disabled in Settings."))

        return {
            'name': _('Register Advance Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_type': 'outbound',
                'default_partner_type': 'supplier',
                'default_partner_id': self.partner_id.id,
                'default_amount': self.amount_total - sum(self.advance_payment_ids.mapped('amount')),
                'default_purchase_order_id': self.id,
                'default_ref': self.name,
            }
        }

    def action_view_advance_payments(self):
        self.ensure_one()
        return {
            'name': _('Advance Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('purchase_order_id', '=', self.id)],
            'context': {'create': False}
        }
