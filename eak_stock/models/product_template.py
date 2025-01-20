# -*- coding: utf-8 -*-

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_sap_code = fields.Char(string='SAP Code')
    x_part_number = fields.Char(string='Part Number')

class ProductProduct(models.Model):
    _inherit = 'product.product'
    x_sap_code = fields.Char(related='product_tmpl_id.x_sap_code', string='SAP Code', readonly=False)
    x_part_number = fields.Char(related='product_tmpl_id.x_part_number', string='Part Number', readonly=False)
