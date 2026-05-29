{
    'name': 'RV Notification Central Management',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Centralized push notification management for all modules',
    'description': """
        This module provides a central dashboard to manage mobile push notifications.
        - Define specific recipients (Global Admin & Secondary User) for various system events.
        - Supports CRM (Leads), Project (Tasks), Sale, Purchase, and Inventory.
        - Unified logic to prevent redundant self-notifications.
    """,
    'author': 'Antigravity',
    'depends': [
        'rv_flutter_notification_bridge',
        'crm',
        'project',
        'sale_management',
        'stock',
        'purchase',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/notification_event_data.xml',
        'views/notification_event_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
