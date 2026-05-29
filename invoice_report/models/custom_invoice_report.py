from odoo import models, api
from urllib.parse import quote_plus

class ReportCustomInvoice(models.AbstractModel):
    _name = 'report.invoice_report.report_custom_invoice'
    _description = 'Custom Invoice Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'url_quote': quote_plus,
        }
