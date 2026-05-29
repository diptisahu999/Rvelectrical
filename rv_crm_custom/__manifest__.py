{
    'name': 'RV CRM Custom',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Customizations for CRM',
    'description': """
        This module contains customizations for CRM.
        - Removes 'Enrich' button.
        - Removes 'Property 1' (lead_properties) field.
    """,
    'depends': [
        'crm', 
        'crm_iap_enrich',
        'hr_timesheet',
        'survey',
        'hr_attendance',
        'hr_holidays',
        # 'data_cleaning',
    ],
    'data': [
        'security/crm_lead_followup_security.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
        'views/hide_menus.xml',
        'views/crm_lead_followup_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
