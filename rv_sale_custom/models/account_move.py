# pyrefly: ignore [missing-import]
from odoo import models, api, fields, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    amount_additional_charge = fields.Monetary(
        string="Additional Charge Amount",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id"
    )
    amount_untaxed = fields.Monetary(
        compute='_compute_amount',
        store=True,
    )
    amount_total = fields.Monetary(
        compute='_compute_amount',
        store=True,
    )
    tax_totals = fields.Binary(
        compute='_compute_tax_totals',
        exportable=False,
    )

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        base_lines, tax_lines = super()._get_rounded_base_and_tax_lines(round_from_tax_lines=round_from_tax_lines)
        base_lines = [line for line in base_lines if not line['record'].is_additional_charge]
        return base_lines, tax_lines

    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.is_additional_charge',
        'line_ids.price_subtotal'
    )
    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            additional_charge = sum(line.price_subtotal for line in move.invoice_line_ids if line.is_additional_charge)
            move.amount_additional_charge = additional_charge
            move.amount_untaxed = sum(line.price_subtotal for line in move.invoice_line_ids if not line.is_additional_charge)
            move.amount_total = move.amount_untaxed + move.amount_tax + additional_charge

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_total', 'invoice_line_ids.is_additional_charge')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            additional_charge = sum(line.price_subtotal for line in move.invoice_line_ids if line.is_additional_charge)
            if additional_charge and move.tax_totals:
                tax_totals = dict(move.tax_totals)
                if 'subtotals' in tax_totals:
                    subtotals = list(tax_totals['subtotals'])
                    subtotals.append({
                        'name': _("Additional Charge"),
                        'base_amount_currency': additional_charge,
                        'base_amount': additional_charge,
                        'tax_amount_currency': 0.0,
                        'tax_amount': 0.0,
                        'tax_groups': [],
                    })
                    tax_totals['subtotals'] = subtotals
                    tax_totals['total_amount_currency'] += additional_charge
                    tax_totals['total_amount'] += additional_charge
                    move.tax_totals = tax_totals

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_additional_charge = fields.Boolean(
        string="Add. Charge",
        help="Check this box if this invoice line is an additional charge product.",
        default=False
    )

    @api.onchange('is_additional_charge')
    def _onchange_is_additional_charge(self):
        if self.is_additional_charge:
            max_seq = max(self.move_id.invoice_line_ids.mapped('sequence') or [0])
            self.sequence = max_seq + 100
        else:
            self.sequence = 10
