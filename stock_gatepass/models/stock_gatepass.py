# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class GatePassType(models.Model):
    _name = 'stock.gatepass.type'
    _description = 'Gate Pass Type'
    _order = 'name'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    is_returnable = fields.Boolean('Is Returnable', default=False,
                                   help="Check this if the gate pass is for materials that should return.")
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company)
    note = fields.Text('Description')


class StockGatePass(models.Model):
    _name = 'stock.gatepass'
    _description = 'Stock Gate Pass'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Name', copy=False, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('expired', 'Expired'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True, copy=False)
    gatepass_type_id = fields.Many2one('stock.gatepass.type', 'Gate Pass Type', required=True)
    is_returnable = fields.Boolean('Is Returnable', related='gatepass_type_id.is_returnable', store=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    source_location_id = fields.Many2one('stock.location', 'Source Location', required=True,
                                         domain=[('usage', '=', 'internal')])
    destination_location_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    issue_date = fields.Date('Issue Date', default=fields.Date.context_today)
    expected_return_date = fields.Date('Expected Return Date')
    actual_return_date = fields.Date('Actual Return Date', readonly=True)
    shipping_policy = fields.Selection([
        ('ship', 'Deliver each product when available'),
        ('direct', 'Deliver all products at once')],
        string='Shipping Policy', required=True, default='direct')
    move_ids = fields.One2many('stock.move', 'gatepass_id', 'Stock Moves')
    picking_ids = fields.One2many('stock.picking', 'gatepass_id', 'Stock Pickings')
    picking_count = fields.Integer('Pickings', compute='_compute_picking_count')
    return_count = fields.Integer('Returns', compute='_compute_return_count')
    note = fields.Text('Notes')
    returned = fields.Boolean('Returned', default=False, copy=False)
    approved_by = fields.Many2one('res.users', 'Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime('Approved Date', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.gatepass') or _('New')
            if not vals.get('destination_location_id', False):
                vals['destination_location_id'] = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1).id
            print(vals.get('move_ids', []))
            for move in vals.get('move_ids', []):
                move[2]['location_id'] = vals.get('source_location_id', False)
                move[2]['location_dest_id'] = vals.get('destination_location_id', False)

        return super(StockGatePass, self).create(vals_list)

    def _compute_picking_count(self):
        for gatepass in self:
            gatepass.picking_count = len(gatepass.picking_ids)

    def _compute_return_count(self):
        for gatepass in self:
            return_count = self.env['stock.picking'].search_count([
                ('gatepass_id', '=', gatepass.id),
                ('gatepass_return', '=', True)
            ])
            gatepass.return_count = return_count

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            'name': _('Pickings'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('gatepass_id', '=', self.id)],
            'context': {'default_gatepass_id': self.id}
        }
        return action

    def action_view_returns(self):
        self.ensure_one()
        action = {
            'name': _('Returns'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('gatepass_id', '=', self.id), ('gatepass_return', '=', True)],
            'context': {'default_gatepass_id': self.id, 'default_gatepass_return': True}
        }
        return action

    def action_submit(self):
        for gatepass in self:
            if not gatepass.move_ids:
                raise UserError(_('Please add at least one product to continue.'))
            gatepass.write({'state': 'submit'})

    def create_delivery_order(self, gatepass):
        picking_vals = {
            'partner_id': gatepass.partner_id.id,
            'picking_type_id': self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', gatepass.company_id.id)
            ], limit=1).id,
            'location_id': gatepass.source_location_id.id,
            'location_dest_id': gatepass.destination_location_id.id,
            'gatepass_id': gatepass.id,
            'scheduled_date': fields.Datetime.now(),
            'origin': gatepass.name,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock moves for each product in the gate pass
        for move in gatepass.move_ids:
            self.env['stock.move'].create({
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'picking_id': picking.id,
                'location_id': gatepass.source_location_id.id,
                'location_dest_id': gatepass.destination_location_id.id,
                'gatepass_id': gatepass.id,
            })

    def create_incoming_shipment(self, gatepass):
        picking_vals = {
            'partner_id': gatepass.partner_id.id,
            'picking_type_id': self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', gatepass.company_id.id)
            ], limit=1).id,
            'location_id': gatepass.destination_location_id.id,
            'location_dest_id': gatepass.source_location_id.id,
            'gatepass_id': gatepass.id,
            'scheduled_date': fields.Datetime.now(),
            'origin': gatepass.name,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock moves for each product in the gate pass
        for move in gatepass.move_ids:
            self.env['stock.move'].create({
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'picking_id': picking.id,
                'location_id': gatepass.destination_location_id.id,
                'location_dest_id': gatepass.source_location_id.id,
                'gatepass_id': gatepass.id,
            })

    def action_confirm(self):
        for gatepass in self:
            if not gatepass.move_ids:
                raise UserError(_('Please add at least one product to continue.'))

            if not gatepass.picking_ids:
                self.create_delivery_order(gatepass)

            if gatepass.gatepass_type_id and gatepass.gatepass_type_id.is_returnable:
                self.create_incoming_shipment(gatepass)

            gatepass.write({
                'state': 'confirmed',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now()
            })

    def action_create_return(self):
        self.ensure_one()
        if not self.is_returnable:
            raise UserError(_('This gate pass is not returnable.'))

        return {
            'name': _('Create Return'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gatepass.return.wizard',
            'target': 'new',
            'context': {'default_gatepass_id': self.id},
        }

    def action_done(self):
        for gatepass in self:
            if gatepass.is_returnable and not gatepass.returned:
                raise UserError(_('This gate pass requires a return. Please create a return first.'))
            gatepass.write({'state': 'done'})

    def action_cancel(self):
        for gatepass in self:
            if any(picking.state == 'done' for picking in gatepass.picking_ids):
                raise UserError(_('Cannot cancel a gate pass with completed pickings.'))
            gatepass.write({'state': 'cancel'})

    @api.onchange('gatepass_type_id')
    def _onchange_gatepass_type(self):
        if self.gatepass_type_id and self.gatepass_type_id.is_returnable:
            self.expected_return_date = fields.Date.context_today(self) + timedelta(days=7)
        else:
            self.expected_return_date = False

    @api.model
    def _check_expiry(self):
        """Cron job to check expired gate passes"""
        today = fields.Date.context_today(self)
        gate_passes = self.search([
            ('state', 'in', ['confirmed', 'submit']),
            ('is_returnable', '=', True),
            ('expected_return_date', '<', today),
            ('returned', '=', False)
        ])
        for gate_pass in gate_passes:
            gate_pass.write({'state': 'expired'})

    @api.constrains('is_returnable', 'expected_return_date')
    def _check_return_date(self):
        """Enforce return date requirement for returnable gate passes"""
        for record in self:
            if record.is_returnable and not record.expected_return_date:
                raise ValidationError(_("Expected return date is required for returnable gate passes."))


class StockMove(models.Model):
    _inherit = 'stock.move'

    gatepass_id = fields.Many2one('stock.gatepass', 'Gate Pass')
