from odoo import models, fields, api

class ImportStageTemplateWizard(models.TransientModel):
    _name = 'import.stage.template.wizard'
    _description = 'Import Stage Template Wizard'

    project_id = fields.Many2one('project.project', string='Project', required=True)
    template_id = fields.Many2one('project.stage.template', string='Stage Template', required=True)
    replace_existing = fields.Boolean('Replace Existing Stages', default=False,
                                    help='If checked, existing stages will be removed before importing template stages')
    import_mode = fields.Selection([
        ('append', 'Add to existing stages'),
        ('replace', 'Replace all existing stages')
    ], string='Import Mode', default='append', required=True)

    @api.model
    def default_get(self, fields):
        """Set default project based on context"""
        res = super().default_get(fields)
        
        # Get project from context - try multiple sources
        project_id = (
            self.env.context.get('default_project_id') or
            self.env.context.get('active_id') if self.env.context.get('active_model') == 'project.project' else None
        )
        
        if project_id:
            res['project_id'] = project_id
        
        return res

    def action_import_stages(self):
        """Import stages from the selected template"""
        if not self.template_id or not self.project_id:
            return {'type': 'ir.actions.act_window_close'}

        # Replace existing stages if requested
        if self.import_mode == 'replace':
            existing_stages = self.env['project.task.type'].search([
                ('project_ids', 'in', self.project_id.id)
            ])
            for stage in existing_stages:
                stage.write({'project_ids': [(3, self.project_id.id)]})

        # Import stages from template
        sequence = 10
        if self.import_mode == 'append':
            # Get the max sequence from existing stages
            existing_stages = self.env['project.task.type'].search([
                ('project_ids', 'in', self.project_id.id)
            ])
            if existing_stages:
                sequence = max(existing_stages.mapped('sequence') or [0]) + 10

        for template_stage in self.template_id.stage_ids.sorted('sequence'):
            # Check if stage with same name already exists
            existing_stage = self.env['project.task.type'].search([
                ('name', '=', template_stage.name),
                ('project_ids', 'in', self.project_id.id)
            ], limit=1)
            
            if not existing_stage:
                self.env['project.task.type'].create({
                    'name': template_stage.name,
                    'description': template_stage.description,
                    'sequence': sequence,
                    'project_ids': [(4, self.project_id.id)],
                })
                sequence += 10

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'Stages imported from template "{self.template_id.name}"',
                'type': 'success',
                'sticky': False,
            }
        }
