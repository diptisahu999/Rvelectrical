from odoo import models

# Hide the "Project Stages" menu from the Project module configure menu
class projectMenu(models.Model):
    _inherit = "ir.ui.menu"
    
    def _filter_visible_menus(self):
        menus = super()._filter_visible_menus()

        xml_ids = [
            'project.menu_project_config_project_stage',
            'project.menu_projects_config_group_stage',
            'project.menu_projects_config',
        ]

        menu_ids = [
            self.env.ref(x, raise_if_not_found=False).id
            for x in xml_ids
            if self.env.ref(x, raise_if_not_found=False)
        ]

        return menus.filtered(lambda m: m.id not in menu_ids)