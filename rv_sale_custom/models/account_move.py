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
            additional_lines = move.invoice_line_ids.filtered(lambda l: l.is_additional_charge)
            if not additional_lines or not move.tax_totals:
                continue

            additional_charge = sum(line.price_subtotal for line in additional_lines)
            non_additional_untaxed = sum(
                line.price_subtotal for line in move.invoice_line_ids
                if not line.is_additional_charge
            )

            tax_totals = dict(move.tax_totals)
            tax_amount = tax_totals.get('tax_amount_currency', 0.0)
            correct_total = non_additional_untaxed + tax_amount + additional_charge

            # Rebuild subtotals: fix Untaxed Amount base, remove stale Additional Charge rows
            new_subtotals = []
            for subtotal in list(tax_totals.get('subtotals', [])):
                if subtotal.get('name') == _("Additional Charge"):
                    continue  # skip any stale Additional Charge row
                if subtotal.get('name') == 'Untaxed Amount':
                    subtotal = dict(subtotal)
                    subtotal['base_amount_currency'] = non_additional_untaxed
                    subtotal['base_amount'] = non_additional_untaxed
                new_subtotals.append(subtotal)

            # Add the Additional Charge subtotal row
            new_subtotals.append({
                'name': _("Additional Charge"),
                'base_amount_currency': additional_charge,
                'base_amount': additional_charge,
                'tax_amount_currency': 0.0,
                'tax_amount': 0.0,
                'tax_groups': [],
            })

            tax_totals['subtotals'] = new_subtotals
            tax_totals['base_amount_currency'] = non_additional_untaxed
            tax_totals['base_amount'] = non_additional_untaxed
            tax_totals['total_amount_currency'] = correct_total
            tax_totals['total_amount'] = correct_total
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
