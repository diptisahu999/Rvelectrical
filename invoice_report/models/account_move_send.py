from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_default_mail_attachments_widget(self, move, mail_template, invoice_edi_format=None, extra_edis=None, pdf_report=None):
        """Override to filter out .json e-invoice attachments from the selection."""
        res = super()._get_default_mail_attachments_widget(
            move, mail_template, 
            invoice_edi_format=invoice_edi_format, 
            extra_edis=extra_edis, 
            pdf_report=pdf_report
        )
        return res

    def _get_invoice_extra_attachments(self, move):
        """Override to filter out .json attachments from the record level attachments."""
        result = super()._get_invoice_extra_attachments(move)
        return result
