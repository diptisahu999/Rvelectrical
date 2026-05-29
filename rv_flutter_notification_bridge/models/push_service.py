from odoo import models
from firebase_admin import messaging
from ..utils.fcm import send_push


class PushService(models.AbstractModel):
    _name = 'push.service'
    _description = 'Push Notification Service'

    # -------------------------
    # SINGLE USER
    # -------------------------
    def send_to_user(self, user_id, title, body, data=None):
        Device = self.env['push.device'].sudo()
        device = Device.search([('user_id', '=', user_id)], limit=1)

        if not device:
            self.env['push.notification.log'].sudo().create({
                'user_id': user_id,
                'title': title,
                'body': body,
                'status': 'no_device',
                'data_payload': str(data)
            })
            return {"status": "no_device"}

        try:
            firebase_id = send_push(
                self.env,
                device.fcm_token,
                title,
                body,
                data or {"user_id": str(user_id)}
            )
            self.env['push.notification.log'].sudo().create({
                'user_id': user_id,
                'title': title,
                'body': body,
                'status': 'success',
                'firebase_id': firebase_id,
                'data_payload': str(data)
            })
            return {"status": "success", "firebase_id": firebase_id}

        except messaging.UnregisteredError:
            device.unlink()
            self.env['push.notification.log'].sudo().create({
                'user_id': user_id,
                'title': title,
                'body': body,
                'status': 'invalid_token',
                'data_payload': str(data)
            })
            return {"status": "invalid_token"}

        except Exception as e:
            self.env['push.notification.log'].sudo().create({
                'user_id': user_id,
                'title': title,
                'body': body,
                'status': 'failed',
                'error_message': str(e),
                'data_payload': str(data)
            })
            return {"status": "failed", "error": str(e)}

    # -------------------------
    # MULTIPLE USERS
    # -------------------------
    def send_to_users(self, user_ids, title, body, data=None):
        results = {
            "success": [],
            "failed": [],
            "invalid": []
        }

        for user_id in user_ids:
            res = self.send_to_user(user_id, title, body, data)

            if res["status"] == "success":
                results["success"].append(user_id)
            elif res["status"] == "invalid_token":
                results["invalid"].append(user_id)
            else:
                results["failed"].append({
                    "user_id": user_id,
                    "error": res.get("error")
                })

        return results


# Action User

# self.env['push.service'].send_to_users(
#     user_ids=[1, 3, 7],
#     title="System Update",
#     body="Maintenance tonight"
# )
