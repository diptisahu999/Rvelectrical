# pyrefly: ignore [missing-import]
from odoo import models, api, fields, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    amount_additional_charge = fields.Monetary(
        string="Additional Charge Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id"
    )

    def _get_priced_lines(self):
        lines = super()._get_priced_lines()
        return lines.filtered(lambda x: not x.is_additional_charge)

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.is_additional_charge')
    def _compute_amounts(self):
        super()._compute_amounts()
        for order in self:
            additional_charge = sum(line.price_subtotal for line in order.order_line if line.is_additional_charge)
            order.amount_additional_charge = additional_charge
            order.amount_total += additional_charge

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.is_additional_charge')
    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for order in self:
            additional_charge = sum(line.price_subtotal for line in order.order_line if line.is_additional_charge)
            if additional_charge and order.tax_totals:
                tax_totals = dict(order.tax_totals)
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
                    order.tax_totals = tax_totals

    def action_confirm(self):
        for order in self:
            # Check if partner is a company and has no GST number (vat)
            if order.partner_id.company_type == 'company' and not order.partner_id.vat:
                raise ValidationError(_("Please add GST number for company contact: %s") % order.partner_id.name)
        
        return super(SaleOrder, self).action_confirm()

    @api.onchange('partner_id')
    def _onchange_partner_id_reset_shipping(self):
        """
        When the customer changes, reset the delivery address if it no longer
        belongs to the newly selected customer (i.e. it is from a different contact).
        """
        if self.partner_id and self.partner_shipping_id:
            valid_ids = (
                self.partner_id
                | self.partner_id.child_ids.filtered(
                    lambda c: c.type == 'delivery'
                )
            ).ids
            if self.partner_shipping_id.id not in valid_ids:
                self.partner_shipping_id = self.partner_id

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_additional_charge = fields.Boolean(
        string="Add. Charge",
        help="Check this box if this order line is an additional charge product.",
        default=False
    )

    @api.onchange('is_additional_charge')
    def _onchange_is_additional_charge(self):
        if self.is_additional_charge:
            max_seq = max(self.order_id.order_line.mapped('sequence') or [0])
            self.sequence = max_seq + 100
        else:
            self.sequence = 10

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res['is_additional_charge'] = self.is_additional_charge
        return res

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'state', 'is_additional_charge')
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self:
            if line.state == 'sale' and not line.display_type and line.is_additional_charge:
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
