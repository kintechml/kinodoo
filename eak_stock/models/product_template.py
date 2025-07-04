# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_sap_code = fields.Char(string='SAP Code')
    x_part_number = fields.Char(string='Part Number')

class ProductProduct(models.Model):
    _inherit = 'product.product'
    x_sap_code = fields.Char(related='product_tmpl_id.x_sap_code', string='SAP Code', readonly=False)
    x_part_number = fields.Char(related='product_tmpl_id.x_part_number', string='Part Number', readonly=False)

    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            domain = expression.OR([
                [('name', operator, name)],
                [('default_code', operator, name)],
                [('x_part_number', operator, name)],
            ])
            args = expression.AND([args, domain])

        return self._search(args, limit=limit, access_rights_uid=name_get_uid)
