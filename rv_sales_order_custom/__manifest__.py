{
    'name': 'RV Sales Order Custom',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Customizations for Sales',
    'description': """
        This module contains customizations for Sales.
    """,
    'depends': ['sale'],
    'data': [
        'views/sale_order_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
