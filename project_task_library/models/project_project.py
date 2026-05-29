from odoo import api, fields, models

class ProjectProject(models.Model):
    _inherit = 'project.project'

    x_project_progress = fields.Float(
        string="Progress",
        compute="_compute_x_project_progress",
        help="Calculates progress based on top-level tasks and their sub-tasks completion."
    )

    @api.depends('tasks.is_closed', 'tasks.subtask_completion_percentage', 'tasks.parent_id')
    def _compute_x_project_progress(self):
        for project in self:
            # We only care about top-level tasks (those with no parent)
            top_level_tasks = project.tasks.filtered(lambda t: not t.parent_id)
            if not top_level_tasks:
                project.x_project_progress = 0.0
                continue
            
            total_progress = 0.0
            for task in top_level_tasks:
                if task.child_ids:
                    # If it has sub-tasks, use the sub-task completion percentage
                    total_progress += task.subtask_completion_percentage
                else:
                    # If no sub-tasks, it's either 100% (closed) or 0% (open)
                    total_progress += 1.0 if task.is_closed else 0.0
            
            # Average the progress of all top-level tasks and convert to percentage (0-100)
            project.x_project_progress = (total_progress / len(top_level_tasks)) * 100