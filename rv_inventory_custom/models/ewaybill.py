from odoo import fields, models

class L10nInEWaybill(models.Model):
    _inherit = 'l10n.in.ewaybill'

    invoice_number = fields.Char(related='picking_id.invoice_number', string="Invoice No.", store=True)
