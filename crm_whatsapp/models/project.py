from odoo import models
import requests
import re
import logging

_logger = logging.getLogger(__name__)

class ProjectProject(models.Model):
    _inherit = "project.project"

    def _sanitize_mobile(self, number):
        """Clean and format mobile number with 91 prefix for India."""
        if not number:
            return False
        digits = re.sub(r'\D+', '', number)
        if len(digits) == 10:
            return "91" + digits
        if len(digits) == 12 and digits.startswith("91"):
            return digits
        return False

class ProjectTask(models.Model):
    _inherit = "project.task"

    def action_send_whatsapp_task(self):
        # 🔗 Webhook URL for the 'project_task' template
        url = "https://webhook.whatapi.in/webhook/69ca03d602e28c7ee4fa2d9c"

        for task in self:
            partner = task.partner_id
            if not partner:
                continue

            raw_mobile = partner.mobile or partner.phone
            # Use the sanitize tool from the project model
            mobile = self.env['project.project']._sanitize_mobile(raw_mobile)

            if not mobile:
                continue

            # Mapping for template from platform:
            # {{1}} Customer Name, {{2}} Project Name, {{3}} Task Name
            payload = {
                "to": str(mobile),
                "recipient_type": "individual",
                "type": "template",
                "template": {
                    "language": {
                        "policy": "deterministic",
                        "code": "en_US"
                    },
                    "name": "project_task",
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                { "type": "text", "text": partner.name or "" },         # {{1}}
                                { "type": "text", "text": task.project_id.name or "" }, # {{2}}
                                { "type": "text", "text": task.name or "" }             # {{3}}
                            ]
                        }
                    ]
                }
            }

            try:
                # Send the POST request with the JSON payload
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                task.message_post(body="✅ **WhatsApp Task Sent!** Notification for task '%s' delivered." % task.name)
            except Exception as e:
                _logger.error("❌ WhatsApp failed for Task %s: %s", task.id, str(e))

        return {"type": "ir.actions.client", "tag": "reload"}
