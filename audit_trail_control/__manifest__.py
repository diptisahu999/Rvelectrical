{
    'name': 'Audit Trail Control',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Force Delete Protected Records (Audit Trail, Journal Entries, Invoices)',
    'description': """
        Allows force deletion of protected records via Server Actions:
        - Mail Messages (Audit Trail/Chatter)
        - Journal Entries (Posted)
        - Journal Items (Posted)
        - Invoices (Posted/Draft)
        
        Bypasses 'You cannot remove parts of the audit trail' and other accounting constraints.
        ⚠️ WARNING: Use only for removing test/erroneous data. This breaks audit trail integrity.
    """,
    'author': 'Antigravity',
    'depends': ['mail', 'account'],
    'data': [
        'security/security_data.xml',
        'data/server_actions.xml',
    ],
    'installable': True,
    'application': False,
}
