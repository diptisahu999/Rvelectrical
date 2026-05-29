import firebase_admin
from firebase_admin import credentials, messaging
import json

def get_firebase_app(env):
    # ✅ Prevent multiple initialization
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # ✅ Get JSON from Odoo DB - Settings → Technical → System Parameters - firebase.service.account
    param = env['ir.config_parameter'].sudo().get_param('firebase.service.account')

    if not param:
        raise ValueError("Firebase config not found in system parameters")

    config = json.loads(param)
    cred = credentials.Certificate(config)

    return firebase_admin.initialize_app(cred)


def send_push(env, token, title, body, data=None):
    app = get_firebase_app(env)

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        token=token,
    )

    return messaging.send(message, app=app)