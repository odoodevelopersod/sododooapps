# -*- coding: utf-8 -*-
################################################################################
#
#   SOD Infotech(https://sodinfotech.com/)
#
#
#    This program is under the terms of Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the
#    Software or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
################################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging


class PropertyProperty(models.Model):
    _name = 'property.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char('Property Name', required=True, tracking=True)
    code = fields.Char('Property Code', required=True, tracking=True)
    address = fields.Text('Address', required=True)
    city = fields.Char('City', default='Dubai')
    country_id = fields.Many2one('res.country', 'Country', default=lambda self: self.env.ref('base.ae'))
    
    # Property Details
    property_type = fields.Selection([
        ('apartment', 'Apartment Building'),
        ('villa', 'Villa'),
        ('office', 'Office Building'),
        ('warehouse', 'Warehouse'),
        ('commercial', 'Commercial Building'),
    ], string='Property Type', required=True, default='apartment')
    
    total_flats = fields.Integer('Total Flats', compute='_compute_total_flats', store=True)
    total_rooms = fields.Integer('Total Rooms', compute='_compute_total_rooms', store=True)
    occupied_rooms = fields.Integer('Occupied Rooms', compute='_compute_room_stats', store=True)
    vacant_rooms = fields.Integer('Vacant Rooms', compute='_compute_room_stats', store=True)
    
    # Owner/Landlord Information
    landlord_id = fields.Many2one('res.partner', 'Landlord', 
                                  domain=[('is_company', '=', False), ('supplier_rank', '>', 0)])
    manager_id = fields.Many2one('res.users', 'Property Manager', default=lambda self: self.env.user)
    
    # Financial
    property_value = fields.Monetary('Property Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Relations
    flat_ids = fields.One2many('property.flat', 'property_id', 'Flats')
    collection_ids = fields.One2many('property.collection', 'property_id', 'Collections')
    expense_ids = fields.One2many('account.move', 'property_id', 'Expenses', domain=[('move_type','in', ('in_invoice','in_refund'))])

    # Status
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    ], string='Status', default='draft', tracking=True)
    
    # Computed Financial Fields
    monthly_rent_income = fields.Monetary('Monthly Rent Income', compute='_compute_financial_summary', currency_field='currency_id')
    monthly_expenses = fields.Monetary('Monthly Expenses', compute='_compute_financial_summary', currency_field='currency_id')
    monthly_profit = fields.Monetary('Monthly Profit', compute='_compute_financial_summary', currency_field='currency_id')
    occupancy_rate = fields.Float('Occupancy Rate (%)', compute='_compute_room_stats')
    
    # Images and Attachments
    image = fields.Image('Property Image', max_width=1920, max_height=1920)
    image_medium = fields.Image('Medium-sized Image', related='image', max_width=128, max_height=128, store=True)
    image_small = fields.Image('Small-sized Image', related='image', max_width=64, max_height=64, store=True)
    
    @api.depends('flat_ids', 'flat_ids.active')
    def _compute_total_flats(self):
        for record in self:
            record.total_flats = len(record.flat_ids.filtered('active'))
    
    @api.depends('flat_ids.room_ids', 'flat_ids.active', 'flat_ids.room_ids.active')
    def _compute_total_rooms(self):
        for record in self:
            active_flats = record.flat_ids.filtered('active')
            record.total_rooms = sum(len(flat.room_ids.filtered('active')) for flat in active_flats)
    
    @api.depends('flat_ids.room_ids.status', 'flat_ids.active', 'flat_ids.room_ids.active')
    def _compute_room_stats(self):
        for record in self:
            active_flats = record.flat_ids.filtered('active')
            rooms = active_flats.mapped('room_ids').filtered('active')
            record.occupied_rooms = len(rooms.filtered(lambda r: r.status == 'occupied'))
            record.vacant_rooms = len(rooms.filtered(lambda r: r.status == 'vacant'))
            # Calculate as decimal (0.0 to 1.0) since view uses percentage widget
            record.occupancy_rate = (record.occupied_rooms / record.total_rooms) if record.total_rooms > 0 else 0
    
    # @api.depends('flat_ids.room_ids.rent_amount', 'expense_ids.amount_total')
    def _compute_financial_summary(self):
        for record in self:
            # Monthly rent income from occupied rooms (only active)
            active_flats = record.flat_ids.filtered('active')
            occupied_rooms = active_flats.mapped('room_ids').filtered(lambda r: r.active and r.status == 'occupied')
            record.monthly_rent_income = sum(occupied_rooms.mapped('rent_amount'))
            
            # Monthly expenses (average from last 12 months)
            expenses = record.expense_ids.filtered(
                lambda e: e.invoice_date >= fields.Date.today().replace(day=1) - timedelta(days=365)
            )
            record.monthly_expenses = sum(expenses.mapped('amount_total')) / 12 if expenses else 0
            
            # Monthly profit
            record.monthly_profit = record.monthly_rent_income - record.monthly_expenses
    
    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(_('Property code must be unique!'))
    
    def action_activate(self):
        self.write({'state': 'active'})
        
    def action_maintenance(self):
        self.write({'state': 'maintenance'})
        
    def action_deactivate(self):
        self.write({'state': 'inactive'})
    
    def action_view_flats(self):
        return {
            'name': _('Flats'),
            'view_mode': 'list,form',
            'res_model': 'property.flat',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('active', '=', True)],
            'context': {'default_property_id': self.id}
        }
    
    def action_view_rooms(self):
        return {
            'name': _('Rooms'),
            'view_mode': 'list,form',
            'res_model': 'property.room',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('active', '=', True)],
            'context': {'default_property_id': self.id}
        }
    
    def action_view_collections(self):
        return {
            'name': _('Collections'),
            'view_mode': 'list,form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'domain': [('property_id', '=', self.id), ('active', '=', True)],
            'context': {'default_property_id': self.id}
        }
    
    def name_get(self):
        result = []
        for record in self:
            name = f"[{record.code}] {record.name}"
            result.append((record.id, name))
        return result
    
    @api.model
    def _cron_recalculate_all_computed_fields(self):
        """
        Scheduled action to recalculate all stored computed fields across the property management system.
        This helps fix any cached values that might not reflect archived records correctly.
        """
        _logger = logging.getLogger(__name__)
        _logger.info("Starting recalculation of all property management computed fields...")
        
        try:
            # Recalculate Property computed fields
            properties = self.search([])
            _logger.info(f"Recalculating computed fields for {len(properties)} properties...")
            for prop in properties:
                prop._compute_total_flats()
                prop._compute_total_rooms()
                prop._compute_room_stats()
                prop._compute_financial_summary()
            
            # Recalculate Flat computed fields
            flats = self.env['property.flat'].search([])
            _logger.info(f"Recalculating computed fields for {len(flats)} flats...")
            for flat in flats:
                flat._compute_rooms_count()
                flat._compute_room_stats()
                flat._compute_financial()
                flat._compute_state()
            
            # Recalculate Room computed fields
            rooms = self.env['property.room'].search([])
            _logger.info(f"Recalculating computed fields for {len(rooms)} rooms...")
            for room in rooms:
                room._compute_financial_stats()
            
            # Recalculate Tenant computed fields
            tenants = self.env['property.tenant'].search([])
            _logger.info(f"Recalculating computed fields for {len(tenants)} tenants...")
            for tenant in tenants:
                tenant._compute_agreement_stats()
                tenant._compute_payment_stats()
            
            # Recalculate Agreement computed fields
            agreements = self.env['property.agreement'].search([])
            _logger.info(f"Recalculating computed fields for {len(agreements)} agreements...")
            for agreement in agreements:
                agreement._compute_payment_stats()
            
            _logger.info("Successfully completed recalculation of all computed fields!")
            
        except Exception as e:
            _logger.error(f"Error during computed fields recalculation: {str(e)}")
            raise
    
    def action_recalculate_computed_fields(self):
        """Manual action to recalculate computed fields for the current property and its related records"""
        self.ensure_one()
        
        # Recalculate this property's computed fields
        self._compute_total_flats()
        self._compute_total_rooms()
        self._compute_room_stats()
        self._compute_financial_summary()
        
        # Recalculate all related flats
        for flat in self.flat_ids:
            flat._compute_rooms_count()
            flat._compute_room_stats()
            flat._compute_financial()
            flat._compute_state()
            
            # Recalculate all rooms in each flat
            for room in flat.room_ids:
                room._compute_financial_stats()
        
        # Show success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Statistics Recalculated'),
                'message': _('All computed fields have been recalculated for this property and its related records.'),
                'type': 'success',
            }
        }
