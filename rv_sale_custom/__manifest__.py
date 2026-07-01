{
    'name': 'RV Sale Custom',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customizations for Sales',
    'description': """
        This module contains customizations for Sales.
        - Removes 'New' button from Quotation List and Kanban views.
    """,
    'depends': ['sale', 'account'],
    'data': [
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rv_sale_custom/static/src/css/sale_order_mobile.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
