# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PartnerLedgerLine(models.TransientModel):
    _name = 'partner.ledger.line'
    _description = 'Partner Ledger Line'
    _order = 'date'

    wizard_id = fields.Many2one('report.customer.card', string='Wizard')
    date = fields.Date(string='Date')
    name = fields.Char(string='Voucher')
    ref = fields.Char(string='Reference')
    debit = fields.Float(string='Debit', default=0.0)
    credit = fields.Float(string='Credit', default=0.0)
    balance = fields.Float(string='Balance', default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    payment_id = fields.Many2one('account.payment', string='Payment')
    move_line_id = fields.Many2one('account.move.line', string='Journal Item')
    partner_id = fields.Many2one('res.partner', string='Partner')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    entry_type = fields.Char(string='Type')
    is_initial_balance = fields.Boolean(string='Initial Balance', default=False)

    # For invoice details
    has_invoice_details = fields.Boolean(string='Has Invoice Details', default=False)

    def action_view_document(self):
        self.ensure_one()
        if self.invoice_id:
            return {
                'name': 'Invoice',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
                'target': 'current',
            }
        elif self.payment_id:
            return {
                'name': 'Payment',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': self.payment_id.id,
                'target': 'current',
            }
        elif self.move_id:
            return {
                'name': 'Journal Entry',
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.move_id.id,
                'target': 'current',
            }
        return True