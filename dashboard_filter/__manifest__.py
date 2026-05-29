{
    "name": "Dashboard Filter Today",
    "version": "18.0.1.0.0",
    "summary": "Adds a Today filter in Sales Analysis (for Spreadsheet Dashboard use)",
    "category": "Sales",
    "author": "Braincuber Technologies",
    "license": "LGPL-3",
    "depends": ["sale_management", "spreadsheet"],  # sale_report comes from this
    "data": [
        "views/sale_report_search_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "dashboard_filter/static/src/js/date_filter_patch.js",
        ],
    },
    "installable": True,
    "application": False,
}
