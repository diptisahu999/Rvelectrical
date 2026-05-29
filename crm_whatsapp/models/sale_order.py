from odoo import models, api
import requests
import logging
import re
import os
import time

_logger = logging.getLogger(__name__)

# LIVE SERVER PATH
PDF_SAVE_DIR = "/var/www/pdf"
PUBLIC_BASE_URL = "https://erp.rvelectrical.in/pdfs"

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _sanitize_mobile(self, number):
        if not number:
            return False
        digits = re.sub(r'\D+', '', number)
        if len(digits) == 10:
            return "91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        return False

    def action_send_whatsapp(self):
        url = "https://webhook.whatapi.in/webhook/69143e3e1b9845c02d4b1c35"

        # Validate directory
        if not os.path.exists(PDF_SAVE_DIR):
            _logger.error("PDF directory does NOT exist: %s", PDF_SAVE_DIR)

        for order in self:
            raw_mobile = order.partner_id.mobile or order.partner_id.phone
            mobile = self._sanitize_mobile(raw_mobile)

            if not mobile:
                order.message_post(
                    body=f"🔴 **WhatsApp Error:** No valid mobile number found for partner {order.partner_id.name}."
                )
                continue

            # Ensure data is flushed to DB before PDF generation to catch latest T&C
            order.flush_recordset()

            # Generate PDF bytes using custom report
            report = self.env.ref("invoice_report.action_unified_quotation")
            pdf_content, _ = report._render_qweb_pdf(report.report_name, res_ids=[order.id])

            # Create unique filename to prevent URL caching
            timestamp = int(time.time())
            file_name = f"SalesOrder_{order.name.replace('/', '_')}_{timestamp}.pdf"
            save_path = os.path.join(PDF_SAVE_DIR, file_name)

            # SAVE PDF
            try:
                with open(save_path, "wb") as f:
                    f.write(pdf_content)
                _logger.info("PDF saved: %s", save_path)
            except Exception as e:
                _logger.error("Error saving PDF for %s: %s", order.name, str(e))

            # PUBLIC URL for WhatsApp
            public_url = f"{PUBLIC_BASE_URL}/{file_name}"
            print("Public PDF URL:", public_url)

            title1 = order.partner_id.name or "Customer"
            title2 = order.name
            title3 = order.expected_date.strftime("%d-%m-%Y") if order.expected_date else ""

            params = {
                "number": str(mobile),
                "title1": title1,
                "title2": f"{title2}",
                "title3": f"has been confirmed in our system, Expected delivery date: {title3}",
                "mediaurl": public_url,     # <--- SEND PUBLIC URL
            }

            try:
                resp = requests.post(url, json=params, timeout=20)
                resp.raise_for_status()

                order.message_post(
                    body=f"✅ **WhatsApp Sent!** PDF sent to +{mobile}"
                )
                if order.state == 'draft':
                    order.write({'state': 'sent'})

            except Exception as e:
                order.message_post(
                    body=f"🔴 **WhatsApp Failed:** {str(e)}"
                )
                _logger.error("WhatsApp send failed for order %s: %s", order.name, str(e))

        return {"type": "ir.actions.client", "tag": "reload"}



