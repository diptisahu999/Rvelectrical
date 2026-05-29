# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import re
import logging

_logger = logging.getLogger(__name__)


class TaskLibraryWizard(models.TransientModel):
    """
    Wizard to select task templates to add to a project.
    """
    _name = 'task.library.wizard'
    _description = 'Task Library Add Wizard'

    task_template_ids = fields.Many2many(
        'project.task.template',
        string='Tasks to Add',
        required=True
    )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------
    def _find_default_stage_for_project(self, project):
        """
        Find a sensible default stage for the given project.
        1. Try project-specific stages (via project_ids M2M)
        2. Fallback to any global/shared stage
        """
        Stage = self.env['project.task.type']
        stage = False

        # Step 1: Try stages linked to this project
        if 'project_ids' in Stage._fields:
            stage = Stage.search([('project_ids', 'in', project.id)], order='sequence asc', limit=1)
            if stage:
                _logger.debug(f"Found project-specific stage '{stage.name}' for project '{project.name}'.")
                return stage

        # Step 2: Fallback to a shared/global stage (no restriction)
        stage = Stage.search([], order='sequence asc', limit=1)
        if stage:
            _logger.debug(f"Using global fallback stage '{stage.name}' for project '{project.name}'.")
        else:
            _logger.warning(f"No task stage found for project '{project.name}'.")
        return stage

    # -------------------------------------------------------------------------
    # Helper: Business Day Calculator (Excluding Sundays)
    # -------------------------------------------------------------------------
    def _calculate_deadline_date_from_days(self, days_str):
        """
        Calculates the deadline date starting from TODAY.
        Logic:
           - Start Date: Today
           - Count forward by N days
           - Skip Sundays
        """
        if not days_str:
            return False
            
        match = re.search(r'\d+', str(days_str))
        if not match:
            return False

        days_to_add = int(match.group())
        current_date = fields.Date.context_today(self)
        added_days = 0

        while added_days < days_to_add:
            current_date += timedelta(days=1)
            # 0=Monday, 6=Sunday. We skip Sunday.
            if current_date.weekday() != 6:
                added_days += 1
        
        return current_date

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_add_tasks(self):
        """Creates project tasks and subtasks from selected templates."""
        self.ensure_one()
        project_id = self.env.context.get('active_id')

        if not project_id:
            _logger.warning("Wizard called without active_id (project ID) in context.")
            return {'type': 'ir.actions.act_window_close'}

        project = self.env['project.project'].browse(project_id)
        if not project.exists():
            _logger.error(f"Project with ID {project_id} not found.")
            return {'type': 'ir.actions.act_window_close'}

        # Get default stage
        new_stage = self._find_default_stage_for_project(project)
        if not new_stage:
            raise UserError(_(
                "Could not find any task stage to assign new tasks for project '%s'. "
                "Please configure at least one task stage in Project settings."
            ) % project.display_name)

        task_env = self.env['project.task']
        tasks_created_count = 0
        subtasks_created_count = 0

        # ---------------------------------------------------------------------
        # Create tasks & subtasks
        # ---------------------------------------------------------------------
        for task_template in self.task_template_ids:
            customer_id = task_template.partner_id.id or project.partner_id.id

            # 🛠 CALCULATION 1: Main Task Deadline (Dynamic from TODAY)
            main_task_deadline = False
            if task_template.days_deadline:
                 main_task_deadline = self._calculate_deadline_date_from_days(task_template.days_deadline)
            else:
                 # Fallback to static date if no days string provided (optional behavior)
                 main_task_deadline = task_template.date_deadline

            task_vals = {
                'name': task_template.name,
                'description': task_template.description,
                'user_ids': [(6, 0, task_template.user_ids.ids)],
                'tag_ids': [(6, 0, getattr(task_template, 'tags_ids', []).ids)],
                'project_id': project.id,
                'stage_id': new_stage.id,
                'date_deadline': main_task_deadline,  # Assign calculated date
                'priority': task_template.priority,
                'partner_id': customer_id,
            }

            try:
                new_task = task_env.create(task_vals)
                tasks_created_count += 1
                _logger.info(f"Created task '{new_task.name}' (ID: {new_task.id}) for project '{project.name}'")

                # Create subtasks from templates
                for sub_template in task_template.subtask_template_ids:
                    sub_customer_id = sub_template.partner_id.id or customer_id
                    
                    # 🛠 CALCULATION 2: Sub-task Deadline (Dynamic from TODAY)
                    sub_task_deadline = False
                    if sub_template.days_deadline:
                        sub_task_deadline = self._calculate_deadline_date_from_days(sub_template.days_deadline)
                    else:
                        sub_task_deadline = sub_template.date_deadline

                    subtask_vals = {
                        'name': sub_template.name,
                        'description': sub_template.description,
                        'user_ids': [(6, 0, sub_template.user_ids.ids)],
                        'tag_ids': [(6, 0, getattr(sub_template, 'tags_ids', []).ids)],
                        'project_id': project.id,
                        'stage_id': new_stage.id,
                        'parent_id': new_task.id,
                        'date_deadline': sub_task_deadline, # Assign calculated date
                        'priority': sub_template.priority,
                        'partner_id': sub_customer_id,
                    }
                    task_env.create(subtask_vals)
                    subtasks_created_count += 1

            except Exception as e:
                _logger.error(
                    f"Failed to create task/subtask from template '{task_template.name}': {e}",
                    exc_info=True
                )

        # ---------------------------------------------------------------------
        # Summary notification
        # ---------------------------------------------------------------------
        _logger.info(
            f"Finished adding tasks to project '{project.name}'. "
            f"Created {tasks_created_count} tasks and {subtasks_created_count} subtasks."
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Tasks Added"),
                'message': _("%d tasks and %d subtasks added successfully.")
                           % (tasks_created_count, subtasks_created_count),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
