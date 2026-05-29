{
    "name": "Invoice Report",
    "version": "1.0.0",
    "summary": "Invoice Report",
    'author': "Braincuber Technologies",
    'website': "https://braincuber.com/",
    "depends": ["account", "l10n_in", "l10n_in_edi_ewaybill", "sale_management", "purchase", "base", "sale", "stock", "sale_stock", "purchase_product_matrix"],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/report_paperformat_data.xml",
        # Reports
        "reports/invoice_report.xml",
        "reports/unified_quotation_proforma_report.xml",
        "reports/remove_matrix_report.xml",
        "reports/purchase_order_report_action.xml",
        "reports/ewaybill_report_action.xml",
        "reports/new_custom_quotation_report.xml",
        "reports/payment_receipt_report.xml",
        # Views
        "views/terms_condition_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        # "reports/report_purchasequotation_override.xml",
    ],
    "application": True,
    "sequence": 1,
    "installable": True,
    "auto_install": False,
}
