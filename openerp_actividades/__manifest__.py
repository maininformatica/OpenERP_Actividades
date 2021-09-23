# -*- coding: utf-8 -*-
{
    'name': "OpenERP - Actividades",

    'summary': """
        Addon mail.activity
    """,

    'description': """
        Addon de actividades. Menu directo y visible y al cerrar actividad. Guarda las actividades Cerradas
    """,

    'author': "MAIN INFORMATICA GANDIA SL",
    'website': "http://www.main-informatica.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.5',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'calendar'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode


    'installable': True,
    'auto_install': False,
    'application': False,       
}