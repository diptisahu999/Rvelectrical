{
    "name": "Stock Quant Views",
    "version": "18.0.1.0",
    "category": "Inventory",
    "summary": "Separate Vendor and Customer stock quant list views",
    "description": """
Create separate stock quant list views for:
- Vendor stock (supplier locations)
- Customer stock (customer locations)
- This avoids confusion in On Hand Units.
    """,
    "author": "Techvizor",
    "depends": [
        "stock"
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_quant_simple_list_view.xml",
    ],
    "installable": True,
    "application": False,
}
