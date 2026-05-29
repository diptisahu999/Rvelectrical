{
    'name': 'RV Advance Payment',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Manage Advance Payments for Sales and Purchase Orders',
    'description': """
        Allow advance payments on Sales and Purchase Orders.
        - Enable/Disable in Settings
        - Register Advance Payment from Order
        - List Advance Payments on Order
        - Auto-reconcile logic (via Outstanding Credits)
    """,
    'depends': ['sale', 'purchase', 'account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
