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


class PropertyFlat(models.Model):
    _name = 'property.flat'
    _description = 'Property Flat'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, flat_number'

    name = fields.Char('Flat Name', compute='_compute_name', store=True)
    flat_number = fields.Char('Flat Number', required=True)
    floor = fields.Integer('Floor', required=True)
    
    # Relations
    property_id = fields.Many2one('property.property', 'Property', required=True, ondelete='cascade')
    room_ids = fields.One2many('property.room', 'flat_id', 'Rooms')
    
    # Details
    flat_type = fields.Selection([
        ('studio', 'Studio'),
        ('1bhk', '1 BHK'),
        ('2bhk', '2 BHK'),
        ('3bhk', '3 BHK'),
        ('4bhk', '4+ BHK'),
        ('penthouse', 'Penthouse'),
    ], string='Flat Type', required=True)
    
    total_area = fields.Float('Total Area (Sq.Ft.)')
    balcony_area = fields.Float('Balcony Area (Sq.Ft.)')
    
    # Computed Fields
    rooms_count = fields.Integer('Number of Rooms', compute='_compute_rooms_count', store=True)
    occupied_rooms = fields.Integer('Occupied Rooms', compute='_compute_room_stats', store=True)
    vacant_rooms = fields.Integer('Vacant Rooms', compute='_compute_room_stats', store=True)
    total_rent = fields.Monetary('Total Rent', currency_field='currency_id', compute='_compute_financial', store=True)
    total_parking_charges = fields.Monetary('Total Parking Charges', currency_field='currency_id', compute='_compute_financial', store=True)
    
    # Financial Summary
    total_security_deposit = fields.Monetary('Total Security Deposit', currency_field='currency_id', 
                                            compute='_compute_financial_summary', store=True)
    total_outstanding_dues = fields.Monetary('Total Outstanding Dues', currency_field='currency_id', 
                                            compute='_compute_financial_summary', store=True)
    # Parking Details
    parking_number = fields.Char('Parking Number')
    has_parking = fields.Boolean('Has Parking')
    parking_charges = fields.Monetary('Parking Charges', currency_field='currency_id',
                                      help="Monthly parking charges for this room")
    parking_deposit = fields.Monetary('Parking Remote Deposit', currency_field='currency_id',
                                      help="One-time parking remote deposit")
    
    # Facilities
    has_parking = fields.Boolean('Has Parking')
    parking_slots = fields.Integer('Parking Slots')
    has_balcony = fields.Boolean('Has Balcony')
    has_kitchen = fields.Boolean('Has Kitchen', default=True)
    has_living_room = fields.Boolean('Has Living Room', default=True)
    
    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('partially_occupied', 'Partially Occupied'),
        ('fully_occupied', 'Fully Occupied'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', compute='_compute_state', store=True)
    
    # Financial
    currency_id = fields.Many2one(related='property_id.currency_id')
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Images
    image = fields.Image('Flat Image', max_width=1920, max_height=1920)
    
    @api.depends('property_id', 'flat_number')
    def _compute_name(self):
        for record in self:
            if record.property_id and record.flat_number:
                record.name = f"{record.property_id.name} - Flat {record.flat_number}"
            else:
                record.name = record.flat_number or 'New Flat'
    
    @api.depends('room_ids', 'room_ids.active')
    def _compute_rooms_count(self):
        for record in self:
            record.rooms_count = len(record.room_ids.filtered('active'))
    
    @api.depends('room_ids.status', 'room_ids.active')
    def _compute_room_stats(self):
        for record in self:
            active_rooms = record.room_ids.filtered('active')
            record.occupied_rooms = len(active_rooms.filtered(lambda r: r.status == 'occupied'))
            record.vacant_rooms = len(active_rooms.filtered(lambda r: r.status == 'vacant'))
    
    @api.depends('room_ids.current_rent', 'room_ids.current_agreement_id.parking_charges', 'room_ids.status', 'room_ids.active')
    def _compute_financial(self):
        for record in self:
            active_rooms = record.room_ids.filtered('active')
            occupied_rooms = active_rooms.filtered(lambda r: r.status == 'occupied')
            record.total_rent = sum(occupied_rooms.mapped('current_rent'))
            # Sum parking charges from active agreements
            record.total_parking_charges = sum(occupied_rooms.mapped('current_agreement_id.parking_charges'))
    
    @api.depends('room_ids.status', 'room_ids.active')
    def _compute_state(self):
        for record in self:
            active_rooms = record.room_ids.filtered('active')
            if not active_rooms:
                record.state = 'available'
            elif all(room.status == 'vacant' for room in active_rooms):
                record.state = 'available'
            elif all(room.status == 'occupied' for room in active_rooms):
                record.state = 'fully_occupied'
            else:
                record.state = 'partially_occupied'
    
    @api.depends('room_ids.current_agreement_id.deposit_amount', 'room_ids.current_agreement_id.pending_amount', 'room_ids.active')
    def _compute_financial_summary(self):
        for record in self:
            active_rooms = record.room_ids.filtered('active')
            
            # Calculate total security deposit from active agreements
            total_deposit = 0.0
            for room in active_rooms:
                if room.current_agreement_id and room.current_agreement_id.active:
                    total_deposit += room.current_agreement_id.deposit_amount or 0.0
            record.total_security_deposit = total_deposit
            
            # Calculate total outstanding dues from active agreements
            # Based on complete months (not fractional) minus collections
            total_dues = 0.0
            for room in active_rooms:
                if room.current_agreement_id and room.current_agreement_id.active:
                    total_dues += room.current_agreement_id.pending_amount or 0.0
            record.total_outstanding_dues = total_dues
    
    @api.constrains('property_id', 'flat_number')
    def _check_flat_number_unique(self):
        for record in self:
            if record.property_id and record.flat_number:
                existing = self.search([
                    ('property_id', '=', record.property_id.id),
                    ('flat_number', '=', record.flat_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Flat number must be unique within a property!'))
    
    def action_view_rooms(self):
        return {
            'name': _('Rooms'),
            'view_mode': 'list,form',
            'res_model': 'property.room',
            'type': 'ir.actions.act_window',
            'domain': [('flat_id', '=', self.id), ('active', '=', True)],
            'context': {'default_flat_id': self.id, 'default_property_id': self.property_id.id}
        }
    
    def action_add_room(self):
        return {
            'name': _('Add Room'),
            'view_mode': 'form',
            'res_model': 'property.room',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_flat_id': self.id, 'default_property_id': self.property_id.id}
        }
    
    def write(self, vals):
        """Override write to invalidate parent computed fields when active status changes"""
        result = super().write(vals)
        
        # If active field is being changed, invalidate parent property computed fields
        if 'active' in vals:
            properties_to_recompute = self.mapped('property_id')
            if properties_to_recompute:
                # Force recomputation of property stats
                properties_to_recompute._compute_total_flats()
                properties_to_recompute._compute_total_rooms()
                properties_to_recompute._compute_room_stats()
                properties_to_recompute._compute_financial_summary()
        
        return result
