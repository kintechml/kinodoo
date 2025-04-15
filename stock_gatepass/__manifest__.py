# -*- coding: utf-8 -*-
{
    'name': 'Stock Gate Pass',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Manage gate pass for incoming and outgoing materials',
    'description': """
Stock Gate Pass Management
==========================
This module allows you to manage gate passes for:
- Outgoing materials that are expected to return
- Incoming materials from suppliers/customers
- Track gate pass status and approval process
- Print gate pass documents
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'stock',
        'mail',
        'product',
    ],
    'data': [
        'security/gatepass_security.xml',
        'security/ir.model.access.csv',
        'data/gatepass_sequence.xml',
        'data/mail_template_data.xml',
        'views/stock_gatepass_views.xml',
        'views/stock_picking_views.xml',
        'views/res_company_views.xml',
        'wizard/gatepass_return_wizard_view.xml',
        'report/gatepass_report.xml',
        'report/gatepass_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            # Add any CSS/JS files if needed
        ],
    },
}
