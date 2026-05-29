from odoo import models, api
import requests
import logging
import re
import os # <-- Import OS module for file saving

_logger = logging.getLogger(__name__)

# Define the directory where the PDF will be saved
PDF_SAVE_DIR = "/var/www/pdf"
PUBLIC_BASE_URL = "https://erp.rvelectrical.in/pdfs"

class AccountMove(models.Model):
    _inherit = "account.move"

    def _sanitize_mobile(self, number):
        """Clean and format mobile number with +91 prefix if needed."""
        if not number:
            return False
        digits = re.sub(r'\D+', '', number)
        if len(digits) == 10:
            return "91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        return False

    def action_send_whatsapp_invoice(self):
        url = "https://webhook.whatapi.in/webhook/69143e3e1b9845c02d4b1c35"

        # Check if the save directory exists and is writable
        if not os.path.exists(PDF_SAVE_DIR):
            _logger.error("The PDF save directory does not exist: %s", PDF_SAVE_DIR)
        
        if self.filtered(lambda move: move.state != 'posted'):
             return {"type": "ir.actions.client", "tag": "reload"}
             
        for invoice in self:
            raw_mobile = invoice.partner_id.mobile or invoice.partner_id.phone
            mobile = self._sanitize_mobile(raw_mobile)
            
            if not mobile:
                continue

            # 1. Generate the Invoice PDF
            report = self.env.ref('account.account_invoices')
            pdf_content, _ = report._render_qweb_pdf(report.report_name, res_ids=invoice.ids)
            
            # Use the invoice number, replacing slashes with underscores for a valid filename
            file_name = f"Invoice_{invoice.name.replace('/', '_')}.pdf"
            save_path = os.path.join(PDF_SAVE_DIR, file_name)
            
            # 2. Save the PDF file locally
            if os.path.exists(PDF_SAVE_DIR):
                try:
                    # 'wb' for write binary mode
                    with open(save_path, 'wb') as f:
                        f.write(pdf_content)
                except Exception as e:
                    _logger.error("Error saving PDF file for invoice %s at %s: %s", invoice.name, save_path, str(e))


            # 3. Prepare data and the attached file for the POST request

            public_url = f"{PUBLIC_BASE_URL}/{file_name}"
            print("Public PDF URL:", public_url)
            
            files = {
                # This attaches the generated PDF content for the WhatsApp API
                "file": (file_name, pdf_content, "application/pdf")
            }
            partner_name = invoice.partner_id.name or "Customer"

            data = {
                "number": mobile,
                "title1": invoice.partner_id.name or "",
                "title2": invoice.name,
                "title3": invoice.amount_total,
                "mediaurl": public_url, 
            }

            # 4. Send the POST Request
            try:
                resp = requests.post(url, data=data, timeout=15)
                resp.raise_for_status()

                # ----------------------
                # Chat Message Log
                # ----------------------
                log_msg = (
                    f"✅ **WhatsApp Sent!** Invoice sent successfully to **{partner_name}** "
                    f"at **+{mobile}** with attached PDF: **{file_name}**."
                )
                invoice.message_post(body=log_msg)

            except Exception as e:
                _logger.error("❌ WhatsApp failed for %s: %s", invoice.name, str(e))

        return {"type": "ir.actions.client", "tag": "reload"}
    