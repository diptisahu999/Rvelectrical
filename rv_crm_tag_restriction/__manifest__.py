{
    "name": "CRM Tag Restriction",
    "version": "18.0.1.0.0",
    "category": "CRM",
    "summary": "Restrict CRM Tag creation to selected users only",
    "depends": [
        "base",
        "crm",          # ✅ REQUIRED
    ],
    "data": [
        "security/rv_tag_security.xml",   # group
        "views/crm_lead_view.xml"
    ],
    "installable": True,
    "license": "LGPL-3",
}
