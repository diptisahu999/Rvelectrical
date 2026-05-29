from odoo import models, api
import requests
import logging
import re

_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

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

        for meeting in self:
            partner = meeting.partner_ids[:1]  # take first attendee
            if not partner:
                continue

            raw_mobile = partner.mobile or partner.phone
            mobile = self._sanitize_mobile(raw_mobile)
            print(mobile)
            if not mobile:
                continue

            # message = f"📅 Meeting Reminder:\n\nSubject: {meeting.name}\nDate: {meeting.start.strftime('%d-%m-%Y %H:%M')}\nDuration: {meeting.duration} hr(s)\nAttendee: {partner.name}"

            params = {
                "number": mobile,
                "message": 'test',
                "name": partner.name or "Guest",
                "orderno": meeting.name,
            }

            try:
                resp = requests.get(base_url, params=params, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                _logger.error("WhatsApp sending error for meeting %s: %s", meeting.name, str(e))

        return {"type": "ir.actions.client", "tag": "reload"}
