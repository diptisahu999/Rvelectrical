from odoo import models, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_project(self):
        """Override to remove service product validation"""
        self.ensure_one()
        
        if self.state != 'sale':
            raise UserError(_("The Sales Order must be confirmed to create a project."))
        
        if self.project_id:
            raise UserError(_("This Sales Order is already linked to a project."))
        
        # Service product check removed
        
        project = self.env['project.project'].create({
            'name': self.name,
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
        })
        
        self.project_id = project
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'target': 'current',
        }
