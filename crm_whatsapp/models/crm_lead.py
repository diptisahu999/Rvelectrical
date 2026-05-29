from odoo import models, api, _
import requests
import re
import logging

_logger = logging.getLogger(__name__)

class Lead(models.Model):
    _inherit = 'crm.lead'

    # ✅ Sanitize phone number
    def _sanitize_mobile(self, number):
        if not number:
            return False
        digits = re.sub(r'\D+', '', number)
        if len(digits) == 10:
            return "91" + digits  # Add India country code
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        return False

    # ✅ Send WhatsApp message
    def send_whatsapp_message(self):
        base_url = "https://webhook.whatapi.in/webhook/691bf8db1b9845c02d4f673c"

        for lead in self:

            raw_mobile = lead.mobile or lead.phone
            mobile = self._sanitize_mobile(raw_mobile)

            # -----------------------------------------
            # ⭐ GET SALESPERSON NAME
            salesperson_name = lead.user_id.name or "Not Assigned"

            # ⭐ GET SALESPERSON WORK PHONE
            salesperson_phone = lead.user_id.employee_id.work_phone or ""
            salesperson_phone = self._sanitize_mobile(salesperson_phone)
            # -----------------------------------------

            if not mobile:
                _logger.warning("⚠️ Invalid or missing mobile for lead %s", lead.name)
                continue

            # ✅ Build dynamic data
            title1 = lead.name or ""
            title2 = lead.partner_name or "abs"
            title3 = lead.phone or lead.mobile or ""
            
            params = {
                "number": str(salesperson_name),
                "title1":f"Lead Name:  {title1}",
                "title2":f"Company Name:  {title2}",
                "title3":f"Phone:  {title3}",
            }

            try:
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()

                # ----------------------------------------------
                # SUCCESS LOG (same style as Sale Order screen)
                # ----------------------------------------------
                log_message = (
                    f"✅ **WhatsApp Sent!** Lead Assignment Notification sent successfully to "
                    f"**{lead.partner_name or lead.name}** at **+{mobile}**."
                )
                lead.message_post(body=log_message)
            except Exception as e:
                _logger.error("❌ WhatsApp sending error for lead %s: %s", lead.name, str(e))

        return True

    # ✅ Manual Button Action
    def action_send_whatsapp_lead(self):
        """Triggered manually from the CRM Lead form via the WhatsApp button"""
        self.send_whatsapp_message()
        return {"type": "ir.actions.client", "tag": "reload"}

    # ✅ Trigger WhatsApp Automatically on Create
    @api.model
    def create(self, vals):
        record = super().create(vals)
        try:
            if vals.get("mobile") or vals.get("phone"):
                record.send_whatsapp_message()
        except Exception as e:
            _logger.error("WhatsApp auto-send failed on create: %s", str(e))
        return record

    # # ✅ Trigger WhatsApp Automatically when specific fields are updated
    # def write(self, vals):
    #     res = super().write(vals)
    #     try:
    #         trigger_fields = {"mobile", "phone", "stage_id"}  # customize as needed
    #         if trigger_fields.intersection(vals.keys()):
    #             self.send_whatsapp_message()
    #     except Exception as e:
    #         _logger.error("WhatsApp auto-send failed on update: %s", str(e))
    #     return res

