from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjectStageTemplate(models.Model):
    _name = 'project.stage.template'
    _description = 'Project Stage Template'

    name = fields.Char('Template Name', required=True)
    description = fields.Text('Description')
    active = fields.Boolean('Active', default=True)
    stage_ids = fields.One2many('project.stage.template.stage', 'template_id', string='Stages')

    def apply_to_project(self, project):
        """Apply template to a project, creating stages"""
        stages_created = []
        for stage in self.stage_ids.sorted('sequence'):
            new_stage = self.env['project.task.type'].create({
                'name': stage.name,
                'description': stage.description,
                'fold': stage.fold,
                'sequence': stage.sequence,
                'project_ids': [(4, project.id)],
            })
            stages_created.append(new_stage)
        return stages_created

    @api.model
    def apply_template_to_project(self, template_id, context=None):
        """Apply template to project from JavaScript context"""
        template = self.browse(template_id)
        if not template.exists():
            raise UserError("Template not found")
            
        # Get project from context
        project_id = None
        if context:
            project_id = context.get('default_project_id') or context.get('active_id')
            
        if not project_id:
            # If no project context, return stage info for kanban column creation
            return {
                'stages': [{
                    'name': stage.name,
                    'fold': stage.fold,
                    'sequence': stage.sequence,
                } for stage in template.stage_ids.sorted('sequence')]
            }
            
        project = self.env['project.project'].browse(project_id)
        if not project.exists():
            raise UserError("Project not found")
            
        stages_created = template.apply_to_project(project)
        return {
            'success': True,
            'stages_created': len(stages_created),
            'message': f"Successfully applied template '{template.name}' to project '{project.name}'"
        }

class ProjectStageTemplateStage(models.Model):
    _name = 'project.stage.template.stage'
    _description = 'Project Stage Template Stage'
    _order = 'sequence, id'

    name = fields.Char('Stage Name', required=True)
    description = fields.Text('Description')
    sequence = fields.Integer('Sequence', default=10)
    fold = fields.Boolean('Folded in Kanban', default=False)
    template_id = fields.Many2one('project.stage.template', string='Template', required=True, ondelete='cascade')
