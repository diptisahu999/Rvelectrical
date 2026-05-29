# -*- coding: utf-8 -*-
{
    'name': "Advanced Partner Ledger Report/Partner Ledger Multi Currency",

    'description': """
        ✅ Custom Date Range for Reports.
        ✅ Journals Filtering.
        ✅ Controller Of Showing Invoice Details.
        ✅ Salesperson Filtering.
        ✅ Balance for Total Debits, Credits, and Ending balance.
        ✅ Controller Of Showing Initial Balance & Ending Balance.
        ✅ Views Controller Report.
        """,

    'summary': """
        Custom Date Range for Reports & Journals Filtering & Controller Of Showing Invoice Details &
        Salesperson Filtering & Balance for Total Debits, Credits, and Ending balance & 
        Controller Of Showing Initial Balance & Ending Balance & Views Controller Report.
    """,

    'version': '18.0',

    'license': 'OPL-1',

    'category': 'Accounting',

    'author': "TKN Solutions",

    'website': "https://www.TKN-solution.com",

    'depends': ['base', 'account'],

    # always loaded
    'data': [
        # security
        'security/ir.model.access.csv',
        # views
        'views/partner_ledger_line_view.xml',
        # reports
        'reports/adv_partner_ledger_report_template.xml',
        # wizard
        'wizard/customer_card_report_view.xml',
    ],

    'images': ['static/description/banner.jpg'],
    'price': 45,
    'currency': 'EUR',

    'installable': True,
    'auto_install': False,
    'application': True,

    'sequence': 30,
}
