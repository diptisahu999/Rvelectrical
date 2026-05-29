# -*- coding: utf-8 -*-
from odoo import models, fields

class ProjectTaskTemplate(models.Model):
    """
    This is the main "Task Template" stored in the library.
    """
    _name = 'project.task.template'
    _description = 'Project Task Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    name = fields.Char(
        'Template Name',
        required=True,
        tracking=True
    )
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
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    subtask_template_ids = fields.One2many(
        'project.subtask.template',
        'task_template_id',
        string="Sub-task Templates",
        copy=True
    )