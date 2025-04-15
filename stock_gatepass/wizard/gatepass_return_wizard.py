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
                for move in gatepass.move_ids:
                    product_return_moves.append((0, 0, {
                        'product_id': move.product_id.id,
                        'quantity': move.product_uom_qty,
                        'uom_id': move.product_uom.id,
                        'move_id': move.id,
                    }))
                res['product_return_moves'] = product_return_moves
                
        return res
    
    def _prepare_return_picking(self, gatepass):
        return {
            'partner_id': gatepass.partner_id.id,
            'picking_type_id': self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', gatepass.company_id.id)
            ], limit=1).id,
            'location_id': gatepass.destination_location_id.id,
            'location_dest_id': gatepass.source_location_id.id,
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
                    'location_id': gatepass.destination_location_id.id,
                    'location_dest_id': gatepass.source_location_id.id,
                    'gatepass_id': gatepass.id,
                })
            
            # If all products are being returned fully, mark the gatepass as returned
            total_qty_returned = sum(line.quantity for line in wizard.product_return_moves)
            total_qty_sent = sum(move.product_uom_qty for move in gatepass.move_ids)
            
            if total_qty_returned >= total_qty_sent:
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
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float('Quantity', digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    move_id = fields.Many2one('stock.move', string='Stock Move')
