{
    "name": "Inventory Ship Address",
    "version": "18.0.1.0",
    "category": "Inventory",
    "summary": "Show full Ship To address in Delivery / e-Waybill like Sales Order",
    "author": "Techvizor",
    "depends": [
        "l10n_in_ewaybill_stock",
        "stock",      
    ],
    "data": [
        "views/ewaybill_ship_view.xml",
    ],
    "installable": True,
    "application": False,
}
