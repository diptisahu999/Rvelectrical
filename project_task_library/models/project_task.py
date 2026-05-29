from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class ProjectTask(models.Model):
    _inherit = "project.task"

    # Define the new field
    x_days_left_display = fields.Char(
        string="Time Left (Excl. Sundays)",
        compute='_compute_days_left_display',
        store=False,  # This ensures it recalculates on every page load
    )

    @api.depends('date_deadline')
    def _compute_days_left_display(self):
        """
        Calculates the remaining workdays (excluding Sundays) 
        until the deadline.
        """
        today = fields.Date.today()
        
        for task in self:
            if not task.date_deadline:
                task.x_days_left_display = "No Deadline Set"
                continue

            deadline = task.date_deadline.date()
            
            if deadline < today:
                task.x_days_left_display = "Deadline Passed"
                continue

            # Loop from today until the deadline, counting non-Sundays
            days_left_count = 0
            current_date = today
            
            while current_date < deadline:
                # date.weekday() returns 0 for Monday and 6 for Sunday
                if current_date.weekday() != 6:  # 6 is Sunday
                    days_left_count += 1
                
                # Move to the next day
                current_date += timedelta(days=1)
            
            # Format the display string
            if days_left_count == 1:
                task.x_days_left_display = f"{days_left_count} day left"
            else:
                task.x_days_left_display = f"{days_left_count} days left"

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """
        Override get_view to dynamically remove 'Done' state from the selection
        options for non-Admin users. This hides the button/option in the UI.
        """
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        # Check if 'state' field exists in the view and User is NOT a Manager
        if 'state' in res.get('fields', {}) and not self.env.user.has_group('project.group_project_manager'):
            selection = res['fields']['state']['selection']
            # Remove '1_done' from the selection list
            # We filter the list of tuples [('value', 'Label'), ...]
            new_selection = [item for item in selection if item[0] != '1_done']
            res['fields']['state']['selection'] = new_selection

        return res

    def write(self, vals):
        """
        Override write to enforce permission rules for Task State changes.
        """
        # Enforce state permissions
        if 'state' in vals and vals['state'] == '1_done':
            if not self.env.user.has_group('project.group_project_manager'):
                raise UserError(
                    _("Access Denied: You do not have permission to mark this task as 'Done'.\n\n"
                    "Please mark the task as 'Approved' instead. "
                    "An Administrator will review and mark it as Done.")
                )
        
        return super(ProjectTask, self).write(vals)