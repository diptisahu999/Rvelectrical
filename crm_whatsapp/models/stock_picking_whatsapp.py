from odoo import models, api
import requests
import re
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

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
        base_url = "https://webhook.whatapi.in/webhook/690497f91b9845c02d43907a"

        for picking in self:
            partner = picking.partner_id

            # ✅ Try to get partner from related sale order if not found
            if not partner and picking.origin:
                sale_order = self.env['sale.order'].search([('name', '=', picking.origin)], limit=1)
                if sale_order:
                    partner = sale_order.partner_id

            if not partner:
                continue

            raw_mobile = partner.mobile or partner.phone
            mobile = self._sanitize_mobile(raw_mobile)
            if not mobile:
                continue

            params = {
                "number": mobile,
                "message": "test",
                "name": partner.name or "Customer",
                "delivery": picking.name,
            }

            try:
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                _logger.error("❌ WhatsApp sending error for delivery %s: %s", picking.name, str(e))

        return {"type": "ir.actions.client", "tag": "reload"}
