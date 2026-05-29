{
    'name': 'Dashboard Today Period',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add Today period option to dashboard',
    'description': """
        This module extends the dashboard functionality to include a 'Today' period option
        that shows today's sales records and invoices.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'sale', 'account'],
    'data': [
        'views/dashboard_views.xml',
        'static/src/js/dashboard_today.js',
    ],
    'assets': {
        'web.assets_backend': [
            'dashboard_today_period/static/src/js/relative_today_patch.js',
            'dashboard_today_period/static/src/js/dashboard_today.js',
            'dashboard_today_period/static/src/css/dashboard_today.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}