# -*- coding: utf-8 -*-
{
    'name': 'MRP BoM Product Configurator',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': """Product variant configuration for BoM lines.""",
    'description': """This module adds a product configurator dialog to BoM lines,
    allowing users to select variants and specify custom attribute values.""",
    'author': 'Antigravity',
    'depends': ['mrp', 'purchase_product_configurator'],
    'data': [
        'views/mrp_bom_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mrp_bom_product_configurator/static/src/js/mrp_bom_product_configurator_dialog.js',
            'mrp_bom_product_configurator/static/src/js/mrp_bom_line_product_field.js',
            'mrp_bom_product_configurator/static/src/xml/mrp_bom_product_configurator_dialog.xml',
            'mrp_bom_product_configurator/static/src/css/mrp_bom_product_configurator.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
