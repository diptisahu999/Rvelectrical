{
    'name': 'Sales Target',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Manage monthly sales targets per user',
    'description': """
        Sales Target 
        =======================
        • Assign sales targets to users
        • Monthly & yearly targets
        • Track target amounts per user
    """,
    'author': 'Your Company Name',
    'website': 'https://yourcompany.com',
    'depends': [
        'base', 'sale_management'
    ],
    'data': [
        # 'security/sales_target_groups.xml',
        'security/ir.model.access.csv',
        # 'views/dashboard_team_performance_views.xml',
        'views/sales_target_views.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            #  'rv_sales_target/views/dashboard_team_performance_views.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
