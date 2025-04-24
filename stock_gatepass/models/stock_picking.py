# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    gatepass_id = fields.Many2one('stock.gatepass', 'Gate Pass')
    gatepass_return = fields.Boolean('Is Gate Pass Return', default=False)

    def button_validate(self):
        result = super(StockPicking, self).button_validate()
        for picking in self:
            if picking.gatepass_id and picking.gatepass_return:
                picking.gatepass_id.write({
                    'returned': True,
                    'actual_return_date': fields.Date.context_today(self)
                })
                if picking.gatepass_id.state not in ['done', 'cancel']:
                    picking.gatepass_id.action_done()
        return result

    def action_create_gatepass(self):
        """Create a new gate pass from picking"""
        self.ensure_one()
        if not self.partner_id:
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('Please select a partner before creating a gate pass.')
                }
            }

        # Get default gate pass type
        gatepass_type = self.env['stock.gatepass.type'].search([('is_returnable', '=', False)], limit=1)

        gatepass_vals = {
            'partner_id': self.partner_id.id,
            'warehouse_id': self.location_id.warehouse_id,
            'gatepass_type_id': gatepass_type.id,
            'user_id': self.env.user.id,
            'company_id': self.company_id.id,
            'issue_date': fields.Date.context_today(self),
        }

        gatepass = self.env['stock.gatepass'].create(gatepass_vals)

        # Create moves in gate pass based on picking moves
        for move in self.move_ids_without_package:
            self.env['stock.gatepass.line'].create({
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'gatepass_id': gatepass.id,
            })

        # Link the picking to the gate pass
        self.write({'gatepass_id': gatepass.id})

        return {
            'name': _('Gate Pass'),
            'view_mode': 'form',
            'res_model': 'stock.gatepass',
            'res_id': gatepass.id,
            'type': 'ir.actions.act_window',
        }
