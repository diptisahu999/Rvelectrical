from odoo import models, _
import logging

_logger = logging.getLogger(__name__)

class PushService(models.AbstractModel):
    _inherit = 'push.service'

    def notify_event(self, event_code, record, title=None, body=None, extra_data=None):
        """
        Central method to trigger a notification based on a system event.
        Logic:
        1. Notify User 1 (Global Admin) if set.
        2. Notify User 2 (Event-specific Secondary User) if set.
        3. Notify Task/Lead assignees if applicable (handled in specific models).
        4. Skip notification for the current user (the person performing the action).
        """
        try:
            Event = self.env['push.notification.event'].sudo()
            event = Event.search([('code', '=', event_code), ('is_active', '=', True)], limit=1)
            if not event:
                return

            company = record.company_id if 'company_id' in record._fields else self.env.company
            user_ids = []

            # 1. Add Assignees (User actually assigned to the task/lead)
            if 'user_ids' in record._fields and record.user_ids:
                user_ids.extend(record.user_ids.ids)

            # 2. Add Secondary User (User 2) - ONLY if actor is in the Monitored list
            if event.secondary_user_ids and event.monitored_user_ids:
                if self.env.user.id in event.monitored_user_ids.ids:
                    user_ids.extend(event.secondary_user_ids.ids)

            # 3. Filter out duplicates
            user_ids = list(set(user_ids))

            if not user_ids:
                return

            # 4. Prepare data
            data = {
                'res_id': str(record.id),
                'res_model': record._name,
                'event_code': event_code,
            }
            if extra_data:
                data.update(extra_data)

            # 5. Prepare Body/Title formatting
            if not title:
                title = event.name
            
            if not body:
                if record._name == 'project.task':
                    if record.parent_id:
                        body = _("Parent: %s\nSub-task: %s") % (record.parent_id.name, record.name)
                    else:
                        body = _("Project: %s\nTask: %s") % (record.project_id.name or _("N/A"), record.name)
                elif record._name == 'crm.lead':
                    body = _("Lead: %s\nCustomer: %s") % (record.name, record.partner_id.name or _("New"))
                else:
                    body = _("Update: %s") % record.display_name

            return self.send_to_users(
                user_ids=user_ids,
                title=title,
                body=body,
                data=data
            )
        except Exception as e:
            _logger.error(f"Central Notification failed for event {event_code}: {e}")
