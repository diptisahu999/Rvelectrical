{
    'name': 'RV app access',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customizations for app access',
    'description': """
        This module contains customizations for Sales.
        - Removes 'New' button from Quotation List and Kanban views.
    """,
    'depends': ['sale', 'crm', 'purchase', 'base_accounting_kit', 'dynamic_accounts_report'],
    'data': [
        'security/rv_sale_security.xml',
        'security/rv_purchase_security.xml',
        'security/ir.model.access.csv',
        'data/rv_force_delete_actions.xml',
        'views/ir_ui_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}