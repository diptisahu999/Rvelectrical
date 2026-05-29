# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectSubtaskTemplate(models.Model):
    """
    Stores the template for a sub-task.
    """
    _name = 'project.subtask.template'
    _description = 'Project Sub-task Template'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char('Sub-task Name', required=True)

    task_template_id = fields.Many2one(
        'project.task.template',
        string='Parent Task Template',
        required=True,
        ondelete='cascade'
    )

    # --- Fields to copy to the real sub-task ---
    description = fields.Html('Description')
    user_ids = fields.Many2many(
        'res.users',
        string='Assignees'
    )
    tags_ids = fields.Many2many(
        'project.tags',
        string='Tags'
    )
    date_deadline = fields.Date('Deadline Date')
    days_deadline = fields.Char('Deadline Days')
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'High')],
        string='Priority'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer'
    )
    milestone_id = fields.Many2one(
        'project.milestone',
        string='Milestone',
        domain="[('project_id', '=', False)]"
    )