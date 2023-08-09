import logging

from odoo import models
from odoo.tools.float_utils import float_is_zero
from odoo.tools.misc import OrderedSet

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = "stock.move"

    def _force_assign(self):
        StockMove = self.env['stock.move']
        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        # Read the `reserved_availability` field of the moves out of the loop to prevent unwanted
        # cache invalidation when actually reserving the move.
        reserved_availability = {move: move.reserved_availability for move in self}
        move_line_vals_list = []
        # Once the quantities are assigned, we want to find a better destination location thanks
        # to the putaway rules. This redirection will be applied on moves of `moves_to_redirect`.
        moves_to_redirect = OrderedSet()
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
            missing_reserved_uom_quantity = move.product_uom_qty - reserved_availability[move]
            missing_reserved_quantity = move.product_uom._compute_quantity(missing_reserved_uom_quantity,
                                                                           move.product_id.uom_id,
                                                                           rounding_method='HALF-UP')
            # create the move line(s) but do not impact quants
            if move.move_orig_ids:
                available_move_lines = move._get_available_move_lines(assigned_moves_ids,
                                                                      partially_available_moves_ids)
                for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
                    qty_added = min(missing_reserved_quantity, quantity)
                    move_line_vals = move._prepare_move_line_vals(qty_added)
                    move_line_vals.update({
                        'location_id': location_id.id,
                        'lot_id': lot_id.id,
                        'lot_name': lot_id.name,
                        'owner_id': owner_id.id,
                        'qty_done': move_line_vals['product_uom_qty']
                    })
                    move_line_vals.pop('product_uom_qty', None)
                    move_line_vals_list.append(move_line_vals)
                    missing_reserved_quantity -= qty_added
                    if float_is_zero(missing_reserved_quantity, precision_rounding=move.product_id.uom_id.rounding):
                        break
            if missing_reserved_quantity:
                to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
                                                                   ml.location_id == move.location_id and
                                                                   ml.location_dest_id == move.location_dest_id and
                                                                   ml.picking_id == move.picking_id and
                                                                   not ml.lot_id and
                                                                   not ml.package_id and
                                                                   not ml.owner_id)
                if to_update:
                    to_update[0].qty_done += move.product_id.uom_id._compute_quantity(
                        missing_reserved_quantity, move.product_uom, rounding_method='HALF-UP')
                else:
                    vals = move._prepare_move_line_vals(quantity=missing_reserved_quantity)
                    vals = dict(vals, qty_done=vals['product_uom_qty'])
                    vals.pop('product_uom_qty', None)
                    move_line_vals_list.append(vals)
            assigned_moves_ids.add(move.id)
            moves_to_redirect.add(move.id)
            if move.product_id.tracking == 'serial':
                move.next_serial_count = move.product_uom_qty

        self.env['stock.move.line'].create(move_line_vals_list)
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        if not self.env.context.get('bypass_entire_pack'):
            self.mapped('picking_id')._check_entire_pack()
        StockMove.browse(moves_to_redirect).move_line_ids._apply_putaway_strategy()
