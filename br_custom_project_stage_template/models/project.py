from odoo import models, fields, api

class Project(models.Model):
    _inherit = 'project.project'

    stage_template_id = fields.Many2one('project.stage.template', string='Stage Template')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to apply stage template if specified"""
        projects = super().create(vals_list)
        
        for project, vals in zip(projects, vals_list):
            if vals.get('stage_template_id'):
                template = self.env['project.stage.template'].browse(vals['stage_template_id'])
                template.apply_to_project(project)
        
        return projects

    def action_apply_stage_template(self):
        """Action to apply a stage template to existing project"""
        return {
            'name': 'Apply Stage Template',
            'type': 'ir.actions.act_window',
            'res_model': 'project.stage.template.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }
    
    @api.model
    def get_project_kanban_examples(self):
        """Get kanban examples including custom stage templates"""
        # Get standard examples (if any exist)
        examples = super().get_project_kanban_examples() if hasattr(super(), 'get_project_kanban_examples') else {}
        
        # Add custom stage templates to examples
        templates = self.env['project.stage.template'].search([('active', '=', True)])
        
        for template in templates:
            # Create stages data for the template
            stages = []
            for stage in template.stage_ids.sorted('sequence'):
                stages.append({
                    'name': stage.name,
                    'tasks': []  # Empty tasks for template
                })
            
            # Add template to examples with a custom key
            template_key = f'template_{template.id}'
            examples[template_key] = {
                'name': template.name,
                'description': template.description or f'Custom template: {template.name}',
                'stages': stages,
                'template_id': template.id,  # Store template ID for later use
            }
        
        return examples
    
    def create_project_from_template(self, template_id):
        """Create project stages from selected template"""
        template = self.env['project.stage.template'].browse(template_id)
        if template.exists():
            template.apply_to_project(self)
        return True

class ProjectStageTemplateWizard(models.TransientModel):
    _name = 'project.stage.template.wizard'
    _description = 'Apply Stage Template Wizard'

    project_id = fields.Many2one('project.project', string='Project', required=True)
    template_id = fields.Many2one('project.stage.template', string='Stage Template', required=True)
    replace_existing = fields.Boolean('Replace Existing Stages', default=True,
                                    help='If checked, existing stages will be removed before applying template')

    def apply_template(self):
        """Apply the selected template to the project"""
        if self.replace_existing:
            # Remove existing stages
            existing_stages = self.env['project.task.type'].search([
                ('project_ids', 'in', self.project_id.id)
            ])
            for stage in existing_stages:
                stage.write({'project_ids': [(3, self.project_id.id)]})
        
        # Apply template
        self.template_id.apply_to_project(self.project_id)
        
        return {'type': 'ir.actions.act_window_close'}
