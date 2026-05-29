from odoo import models, api
import requests
import re
import logging

_logger = logging.getLogger(__name__)

class Partner(models.Model):
    _inherit = 'res.partner'

    def _sanitize_mobile(self, number):
        if not number:
            return False
        digits = re.sub(r'\D+', '', number)
        if len(digits) == 10:
            return "91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        return False

    def send_whatsapp_message(self):
        base_url = "https://webhook.whatapi.in/webhook/691bf8db1b9845c02d4f673c"

        for partner in self:
            raw_mobile = partner.mobile or partner.phone
            mobile = partner._sanitize_mobile(raw_mobile)
            
            if not mobile:
                continue

            params = {
                "number": mobile,
                "title1": partner.name or "",
                "title2": "Contact Created",
                "title3": "*",
            }

            try:
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()

                # ------------------------
                # SUCCESS LOG (beautiful)
                # ------------------------
                log_msg = (
                    f"✅ **WhatsApp Sent!** Contact creation message sent successfully to "
                    f"**{partner.name}** at **+{mobile}**."
                )
                partner.message_post(body=log_msg)
            except Exception as e:
                _logger.error("WhatsApp sending error for partner %s: %s", partner.id, str(e))
