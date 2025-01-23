# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_sap_code = fields.Char(string='SAP Code')
    x_part_number = fields.Char(string='Part Number')

class ProductProduct(models.Model):
    _inherit = 'product.product'
    x_sap_code = fields.Char(related='product_tmpl_id.x_sap_code', string='SAP Code', readonly=False)
    x_part_number = fields.Char(related='product_tmpl_id.x_part_number', string='Part Number', readonly=False)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain += ['|', ('name', operator, name),
                     ('x_part_number', operator, name)]
        return self._search(domain, limit=limit, order=order)
