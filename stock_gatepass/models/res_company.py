# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    gatepass_validity_days = fields.Integer(string='Gate Pass Validity (Days)', default=15,
                                           help="Default number of days for gate pass validity")
    gatepass_auto_expire = fields.Boolean(string='Auto Expire Gate Passes', default=True)
    gatepass_approval_required = fields.Boolean(string='Gate Pass Approval Required', default=True)
    gatepass_default_return_location_id = fields.Many2one('stock.location', string='Default Return Location')
