# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GatepassReturnWizard(models.TransientModel):
    _name = 'gatepass.return.wizard'
    _description = 'Gate Pass Return Wizard'

    gatepass_id = fields.Many2one('stock.gatepass', string='Gate Pass', required=True)
    return_date = fields.Date(string='Return Date', default=fields.Date.context_today, required=True)
    product_return_moves = fields.One2many('gatepass.return.line', 'wizard_id', string='Products to Return')

    @api.model
    def default_get(self, fields):
        res = super(GatepassReturnWizard, self).default_get(fields)
        gatepass_id = self.env.context.get('active_id') or self.env.context.get('default_gatepass_id')
        if gatepass_id:
            gatepass = self.env['stock.gatepass'].browse(gatepass_id)
            if gatepass.state != 'confirmed':
                raise UserError(_('You can only return confirmed gate passes.'))
            if not gatepass.is_returnable:
                raise UserError(_('This gate pass is not returnable.'))
            if gatepass.returned:
                raise UserError(_('This gate pass has already been returned.'))

            if 'gatepass_id' in fields:
                res['gatepass_id'] = gatepass_id

            if 'product_return_moves' in fields:
                product_return_moves = []
                for line in gatepass.line_ids:
                    # Calculate remaining quantity to return (original - already returned)
                    remaining_qty = line.product_uom_qty - line.returned_qty
                    if remaining_qty > 0:
                        product_return_moves.append((0, 0, {
                            'quantity': remaining_qty,
                            'uom_id': line.product_uom.id,
                            'line_id': line.id,
                        }))
                res['product_return_moves'] = product_return_moves

        return res

    def _prepare_return_picking(self, gatepass):
        return {
            'partner_id': gatepass.partner_id.id,
            'picking_type_id': gatepass.warehouse_id.out_type_id.return_picking_type_id.id,
            'location_id': self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id,
            'location_dest_id': gatepass.warehouse_id.out_type_id.return_picking_type_id.default_location_dest_id.id,
            'gatepass_id': gatepass.id,
            'gatepass_return': True,
            'origin': _("Return of %s") % gatepass.name,
            'scheduled_date': fields.Datetime.now(),
        }

    def create_returns(self):
        for wizard in self:
            # Check if any quantities are greater than zero
            if not any(line.quantity > 0 for line in wizard.product_return_moves):
                raise UserError(_('Please specify at least one product to return.'))

            gatepass = wizard.gatepass_id
            picking_vals = self._prepare_return_picking(gatepass)
            picking = self.env['stock.picking'].create(picking_vals)

            # Create stock moves for each product being returned
            for line in wizard.product_return_moves.filtered(lambda l: l.quantity > 0):
                self.env['stock.move'].create({
                    'name': _('Return of %s') % line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id,
                    'location_dest_id': gatepass.warehouse_id.out_type_id.return_picking_type_id.default_location_dest_id.id
                })

            # Update the returned_qty on each gate pass line and check if fully returned
            for return_line in wizard.product_return_moves:
                if return_line.line_id and return_line.quantity > 0:
                    return_line.line_id.write({
                        'returned_qty': return_line.line_id.returned_qty + return_line.quantity
                    })

            # Check if all products have been returned
            all_returned = all(
                line.returned_qty >= line.product_uom_qty
                for line in gatepass.line_ids
            )

            if all_returned:
                gatepass.write({
                    'returned': True,
                    'actual_return_date': wizard.return_date
                })

            # Show the created picking
            action = {
                'name': _('Return Picking'),
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'res_id': picking.id,
            }
            return action


class GatepassReturnLine(models.TransientModel):
    _name = 'gatepass.return.line'
    _description = 'Gate Pass Return Line'

    wizard_id = fields.Many2one('gatepass.return.wizard', string='Wizard')
    product_id = fields.Many2one(related='line_id.product_id', string='Product')
    quantity = fields.Float('Quantity', digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    line_id = fields.Many2one('stock.gatepass.line', string='Gate Pass Line')
