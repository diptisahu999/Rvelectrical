{
    'name': 'JustDial Integration',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Integration with JustDial Leads',
    'description': """
        This module provides an endpoint to receive leads from JustDial automatically.
        Endpoint: /lead
    """,
    'author': 'Your Company',
    'depends': ['base', 'crm'],
    'data': [
        'views/justdial_cron.xml',
        'views/res_company_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
