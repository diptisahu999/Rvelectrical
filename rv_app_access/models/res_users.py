from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        for user in users:
            if user.has_group('rv_app_access.group_restricted_sales_access'):
                user.write({
                    'groups_id': [
                        (3, self.env.ref('account.group_account_invoice').id),
                        (3, self.env.ref('account.group_account_readonly').id),
                        (3, self.env.ref('account.group_account_user').id),
                        (3, self.env.ref('account.group_account_manager').id),
                    ]
                })
        return users

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        group_restricted_id = self.env.ref('rv_app_access.group_restricted_sales_access').id
        
        # Check if the restricted group is being added or is already present
        # If 'groups_id' is in vals, we need to analyze the operations.
        # But a simpler check is: after write, if the user has the group, remove the others.
        # This might cause a double-write but guarantees the state.
        
        for user in self:
            if user.has_group('rv_app_access.group_restricted_sales_access'):
                # We need to check if they have any of the accounting groups and remove them
                groups_to_remove = []
                for xml_id in ['account.group_account_invoice', 'account.group_account_readonly', 'account.group_account_user', 'account.group_account_manager']:
                    group = self.env.ref(xml_id, raise_if_not_found=False)
                    if group and user.has_group(xml_id):
                        groups_to_remove.append((3, group.id))
                
                if groups_to_remove:
                    # Write only the changes to groups to avoid recursion loop if managed carefully
                    # Calling super().write inside write can recurse.
                    # We must use a context flag or raw SQL to avoid recursion or just be careful.
                    # 'write' on 'res.users' is frequent.
                    
                    # To avoid recursion, we can check context.
                    if not self._context.get('fixing_restricted_access'):
                        user.with_context(fixing_restricted_access=True).write({'groups_id': groups_to_remove})
                        
        return res
