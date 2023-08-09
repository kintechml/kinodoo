import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    user_ids = fields.Many2many("res.users", domain="[('share', '=', False)]")
