{
    'name': 'RV Inventory Custom',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Customizations for Inventory',
    'description': """
        This module adds a new field 'Purchase Order' to the Inventory Transfers (stock.picking) view,
        mimicking the behavior of the Sales Order field.
    """,
    'author': 'Antigravity',
    'website': 'https://rv.com',
    'depends': ['stock', 'purchase', 'sale_stock', 'purchase_stock', 'l10n_in_ewaybill_stock'],
    'data': [
        'views/stock_picking_views.xml',
        'views/ewaybill_views.xml',
        # 'reports/report_delivery_document.xml',
        'reports/report_ewaybill.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
