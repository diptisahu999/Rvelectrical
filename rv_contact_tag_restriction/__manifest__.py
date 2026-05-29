{
    'name': 'Contact Tag Restriction',
    'version': '18.0.1.0',
    'category': 'Contacts',
    'summary': 'Restrict Contact Tag creation based on User permissions',
    'description': """
Contact Tag Restriction
=======================
✔ Control who can create Contact Tags
✔ Restriction configurable from Settings → Users
✔ Hide "Create" option in Contacts
✔ Show alert if user tries to create tag
✔ Safe for multi-user & production
    """,
    'author': 'Techvizor',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        'security/rv_tag_security.xml',
        'views/res_partner_tag_view.xml',
    ],
    'installable': True,
    'application': False,
}
