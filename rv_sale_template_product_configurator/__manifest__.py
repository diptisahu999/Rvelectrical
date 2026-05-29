{
    'name': 'Sale Template Product Configurator',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Product variant configuration for Sale Order Template lines.',
    'description': """
        This module adds a product configurator dialog to Sale Order Template lines,
        consistent with the one used in MRP BoM lines.
    """,
    'author': 'Antigravity',
    'depends': ['sale_management', 'mrp_bom_product_configurator'],
    'data': [
        'views/sale_order_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rv_sale_template_product_configurator/static/src/js/sale_order_template_line_configurator.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
