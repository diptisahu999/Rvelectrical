{
    'name': 'RV Custom User Menu',
    'version': '18.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Removes unwanted items from the user menu',
    'depends': ['web', 'web_tour'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'rv_custom_user_menu/static/src/user_menu.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
