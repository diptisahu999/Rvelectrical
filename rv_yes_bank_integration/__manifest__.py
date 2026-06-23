# -*- coding: utf-8 -*-
{
    'name': 'YES Bank Integration',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Automated Bank Statement Fetch and Callback for YES Bank',
    'author': 'RV Enterprise',
    'depends': ['base', 'account', 'base_accounting_kit'],
    'data': [
        'security/ir.model.access.csv',
        'views/yes_bank_log_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_journal_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
}
