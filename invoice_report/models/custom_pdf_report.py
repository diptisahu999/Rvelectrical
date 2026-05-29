from odoo import models
import base64
from pypdf import PdfWriter
from io import BytesIO

class ReportMerge(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, content_type = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )

        if report_ref != 'invoice_report.report_unified_quotation_new':
            return pdf_content, content_type

        orders = self.env['sale.order'].browse(res_ids)

        merger = PdfWriter()

        for order in orders:
            template = order.sale_order_template_id

            # ❌ No template → only quotation
            if not template:
                merger.append(BytesIO(pdf_content))
                continue

            documents = template.quotation_document_ids

            # ✅ HEADER FILES
            headers = documents.filtered(lambda d: d.document_type == 'header')

            # ✅ FOOTER FILES
            footers = documents.filtered(lambda d: d.document_type == 'footer')

            # 👉 Add Header PDFs
            for header in headers:
                if header.datas:
                    merger.append(BytesIO(base64.b64decode(header.datas)))

            # 👉 Add Main Quotation (per order)
            single_pdf, _ = super()._render_qweb_pdf(
                report_ref, res_ids=[order.id], data=data
            )
            merger.append(BytesIO(single_pdf))

            # 👉 Add Footer PDFs
            for footer in footers:
                if footer.datas:
                    merger.append(BytesIO(base64.b64decode(footer.datas)))

        output = BytesIO()
        merger.write(output)
        merger.close()

        return output.getvalue(), content_type