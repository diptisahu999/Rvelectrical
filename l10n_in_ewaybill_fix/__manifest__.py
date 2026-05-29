{
    'name': 'Indian E-Waybill Fix',
    'version': '18.0.1.0.0',
    'summary': 'Fixes UQC length issue in E-Waybill',
    'description': """
        Fixes the error: JSON validation failed due to - #/itemList/0/qtyUnit: expected maxLength: 3, actual: 6.
        Overrides the E-waybill generation logic to ensure qtyUnit is always a valid 3-character code.
    """,
    'category': 'Accounting/Localizations',
    'author': 'Antigravity',
    'depends': ['l10n_in_edi_ewaybill'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
