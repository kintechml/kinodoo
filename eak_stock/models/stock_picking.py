import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = "stock.picking"

    transferred = fields.Boolean(string='Transferred', default=False)

    show_transfer = fields.Boolean(
        compute='_compute_show_transfer',
        help='Technical field used to decide whether the button "Transfer" should be displayed.')

    transfer_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('transfer', 'Transfer'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_transfer_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n"
             "(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n"
             "(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n"
             "(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n"
             "(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Transfer: The transfer has been processed.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")

    def button_validate(self):
        _logger.info('stock_picking.button_validate: being called with args: %s', ' '.join(str(item) for item in self))
        for picking in self:
            warehouse = picking.location_id.warehouse_id
            warehouse_dest = picking.location_dest_id.warehouse_id
            _logger.info('Picking state: %s and transferred %s', picking.state, picking.transferred)
            if picking.picking_type_code == 'internal' and not picking.transferred:
                if warehouse.user_ids and self.env.user not in warehouse.user_ids:
                    raise AccessError(
                        _("The %s user don't have access to the %s warehouse") % (self.env.user.name, warehouse.name))
                picking.transferred = True
                return True
            if warehouse_dest.user_ids and self.env.user not in warehouse_dest.user_ids:
                raise AccessError(
                    _("The %s user don't have access to the %s warehouse") % (self.env.user.name, warehouse_dest.name))
            bad_moves = self.mapped('move_line_nosuggest_ids').filtered(lambda move: len(move.location_dest_id.display_name.split('/')) == 2)
            if picking.picking_type_code != 'outgoing' and len(bad_moves) > 0:
                raise UserError(_("Impossible to receive products in a mother location"))
        return super(StockPicking, self).button_validate()

    def action_confirm(self):
        _logger.info('stock_picking.action_confirm: being called with args: %s', ' '.join(str(item) for item in self))
        for picking in self:
            warehouse_dest = picking.location_dest_id.warehouse_id
            _logger.info('Picking state: %s', picking.state)

            if picking.origin and picking.origin[0] in ['P', 'S']:
                continue

            if warehouse_dest.user_ids and self.env.user not in warehouse_dest.user_ids:
                msg = _("The %s user don't have access to the %s warehouse") % (self.env.user.name, warehouse_dest.name)
                raise AccessError(msg)
        return super(StockPicking, self).action_confirm()

    def force_assign(self):
        self.filtered(lambda picking: picking.state == 'draft').action_confirm()
        moves = self.mapped('move_lines').filtered(lambda move: move.state not in ('draft', 'cancel', 'done')).sorted(
            key=lambda move: (-int(move.priority), not bool(move.date_deadline), move.date_deadline, move.date, move.id)
        )
        if not moves:
            raise UserError(_('Nothing to check the availability for.'))
        moves._force_assign()

    @api.depends('transfer_state')
    def _compute_show_validate(self):
        for picking in self:
            if picking.picking_type_code != 'internal':
                super(StockPicking, self)._compute_show_validate()
            elif picking.transfer_state not in 'transfer':
                picking.show_validate = False
            else:
                picking.show_validate = True

    @api.depends('transfer_state')
    def _compute_show_transfer(self):
        for picking in self:
            if picking.picking_type_code != 'internal':
                picking.show_transfer = False
            elif picking.transfer_state not in ('waiting', 'confirmed', 'assigned'):
                picking.show_transfer = False
            else:
                picking.show_transfer = True

    @api.depends('state', 'transferred')
    def _compute_transfer_state(self):
        for picking in self:
            if picking.state in ('waiting', 'confirmed', 'assigned') and picking.transferred:
                picking.transfer_state = 'transfer'
            else:
                picking.transfer_state = picking.state
