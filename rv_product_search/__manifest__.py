{
    'name': 'RV Product Search by Attributes',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Product',
    'summary': 'Instantly search products by attribute values in the search bar',
    'description': """
        This module enhances the product search functionality so that when a user
        types an attribute value (e.g., "590") in the search bar and presses Enter,
        it automatically searches through product attribute values in addition to
        the product name, internal reference, and barcode.

        Without this module, users have to manually select the "Attribute" filter
        from the search dropdown, which is a cumbersome multi-step process.
    """,
    'author': 'RV Enterprise',
    'website': 'https://rv.com',
    'depends': ['product'],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
