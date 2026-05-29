{
    'name': 'Project Stage Templates',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Manage predefined task stage templates for projects',
    'description': """
        Project Stage Templates
        =======================
        
        This module allows you to create and manage predefined task stage templates
        that can be applied to new projects.
        
        Features:
        ---------
        * Create custom stage templates with multiple stages
        * Apply templates when creating new projects
        * Manage templates (add, edit, remove)
        * Predefined common templates for different project types
        
        Usage:
        ------
        1. Go to Project > Configuration > Stage Templates
        2. Create your custom stage templates
        3. When creating a new project, select a template to apply
        4. The project will be created with the template's stages
    """,
    'author': 'Braincuber Technologies Pvt. Ltd.',
    'website': 'https://www.braincuber.com',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'views/stage_template_views.xml',
        'views/import_stage_wizard_views.xml',
        'views/project_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'br_custom_project_stage_template/static/src/js/project_template_integration.js',
        ],
    },
    'demo': [
        'data/stage_template_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
