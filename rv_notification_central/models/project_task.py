from odoo import api, models, _

class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            # Determine if it's a subtask or main task
            code = 'project_subtask_create' if task.parent_id else 'project_task_create'
            self.env['push.service'].sudo().notify_event(
                event_code=code,
                record=task,
            )
        return tasks

    def write(self, vals):
        res = super().write(vals)
        if 'user_ids' in vals:
            for task in self:
                code = 'project_subtask_assign' if task.parent_id else 'project_task_assign'
                self.env['push.service'].sudo().notify_event(
                    event_code=code,
                    record=task,
                )
        return res


