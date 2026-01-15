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


class PropertyRoom(models.Model):
    _name = 'property.room'
    _description = 'Property Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'property_id, flat_id, room_number'

    name = fields.Char('Room Name', compute='_compute_name', store=True)
    room_number = fields.Char('Room Number', required=True)
    
    # Relations
    property_id = fields.Many2one('property.property', 'Property', required=True, ondelete='cascade')
    flat_id = fields.Many2one('property.flat', 'Flat', required=True, ondelete='cascade')
    room_type_id = fields.Many2one('property.room.type', 'Room Type', required=True)
    
    # Current Tenant & Agreement
    current_tenant_id = fields.Many2one('property.tenant', string='Current Tenant', readonly=True, copy=False)
    current_agreement_id = fields.Many2one('property.agreement', string='Current Agreement', readonly=True, copy=False)
    
    
    # Related fields from current agreement for display in lists
    agreement_parking_charges = fields.Monetary('Agreement Parking Charges', 
                                                related='current_agreement_id.parking_charges', 
                                                readonly=True, store=False)
    agreement_deposit = fields.Monetary('Agreement Deposit', 
                                       related='current_agreement_id.deposit_amount', 
                                       readonly=True, store=False)
    
    current_occupants_ids = fields.One2many('property.occupant', compute='_compute_current_occupants', 
                                            string='Room Occupants')
    occupants_count = fields.Integer('Occupants Count', compute='_compute_current_occupants')
    
    # Room Details
    area = fields.Float('Area (Sq.Ft.)')
    rent_amount = fields.Monetary('Monthly Rent', required=True, currency_field='currency_id', tracking=True,)
    deposit_amount = fields.Monetary('Security Deposit', currency_field='currency_id')
    
    # Current Rent (from active agreement if exists, otherwise base rent)
    current_rent = fields.Monetary('Current Monthly Rent', compute='_compute_current_rent', 
                                   currency_field='currency_id', store=False,
                                   help="Current rent from active agreement, or base rent if no active agreement")
    
    # Parking Details
    parking_number = fields.Char('Parking Number')
    has_parking = fields.Boolean('Has Parking')
    parking_charges = fields.Monetary('Parking Charges', currency_field='currency_id',
                                     help="Monthly parking charges for this room")
    parking_deposit = fields.Monetary('Parking Remote Deposit', currency_field='currency_id',
                                     help="One-time parking remote deposit")
    
    # Other Charges (per room)
    cleaning_charges = fields.Monetary('Cleaning Charges', currency_field='currency_id',
                                      help="Monthly cleaning charges for this room")
    extra_person_charges = fields.Monetary('Extra Person Charges', currency_field='currency_id',
                                          help="Charges for additional person in room")
    maintenance_charges = fields.Monetary('Maintenance Charges', currency_field='currency_id',
                                         help="Monthly maintenance charges")
    utility_charges = fields.Monetary('Utility Charges', currency_field='currency_id',
                                     help="Monthly utility charges if not included")
    
    # Other Charges from Master Data
    other_charge_ids = fields.Many2many('property.other.charges', 
                                       'room_other_charge_rel', 
                                       'room_id', 
                                       'charge_id',
                                       string='Additional Charges',
                                       domain="[('active', '=', True)]",
                                       help="Select applicable charges from master list")
    
    # Status
    status = fields.Selection([
        ('vacant', 'Vacant'),
        ('occupied', 'Occupied'),
        ('booked', 'Booked'),
        ('maintenance', 'Under Maintenance'),
        ('not_available', 'Not Available'),
    ], string='Status', default='vacant', required=True, tracking=True)
    
    # Facilities
    has_ac = fields.Boolean('Air Conditioning')
    has_heater = fields.Boolean('Heater')
    has_wardrobe = fields.Boolean('Wardrobe')
    has_desk = fields.Boolean('Desk')
    has_wifi = fields.Boolean('WiFi', default=True)
    has_private_bathroom = fields.Boolean('Private Bathroom')
    has_balcony_access = fields.Boolean('Balcony Access')
    
    # Utilities
    has_gas = fields.Boolean('Gas Included')
    electricity_included = fields.Boolean('Electricity Included')
    water_included = fields.Boolean('Water Included', default=True)
    internet_included = fields.Boolean('Internet Included', default=True)
    
    # Additional Information
    inclusions = fields.Text('Other Inclusions')
    notes = fields.Text('Notes')
    
    # Computed Fields
    currency_id = fields.Many2one(related='property_id.currency_id')
    is_available = fields.Boolean('Available for Rent', compute='_compute_availability')
    days_vacant = fields.Integer('Days Vacant', compute='_compute_days_vacant')
    
        # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Financial Tracking
    total_collected = fields.Monetary('Total Collected', compute='_compute_financial_stats', currency_field='currency_id')
    last_collection_date = fields.Date('Last Collection', compute='_compute_financial_stats')
    pending_amount = fields.Monetary('Pending Amount', compute='_compute_financial_stats', currency_field='currency_id')
    
    # Security deposit and outstanding dues for current tenant
    security_deposit = fields.Monetary('Security Deposit', compute='_compute_tenant_financials', currency_field='currency_id',
                                       help="Security deposit of current tenant")
    outstanding_amount = fields.Monetary('Outstanding Dues', compute='_compute_tenant_financials', currency_field='currency_id',
                                         help="Outstanding dues of current tenant")
    base_rent_amount = fields.Float("Base Rent")

    
    # Images
    image = fields.Image('Room Image', max_width=1920, max_height=1920)
    image_ids = fields.One2many('ir.attachment', 'res_id', 'Additional Images', 
                                domain=[('res_model', '=', 'property.room'), ('mimetype', 'like', 'image/')])

    @api.onchange('cleaning_charges', 'maintenance_charges', 'extra_person_charges', 'utility_charges',
                  'base_rent_amount')
    @api.onchange('cleaning_charges', 'maintenance_charges', 'extra_person_charges', 'utility_charges')
    def _onchange_charges(self):
        for rec in self:
            # Start from the original rent (before extra charges)
            base_rent = rec._origin.rent_amount or rec.rent_amount or 0

            total_charges = (
                    (rec.cleaning_charges or 0)
                    + (rec.maintenance_charges or 0)
                    + (rec.extra_person_charges or 0)
                    + (rec.utility_charges or 0)
            )

            rec.rent_amount = base_rent + total_charges
    
    @api.depends('property_id', 'flat_id', 'room_number')
    def _compute_name(self):
        for record in self:
            if record.property_id and record.flat_id and record.room_number:
                record.name = f"{record.property_id.code}-{record.flat_id.flat_number}-{record.room_number}"
            else:
                record.name = record.room_number or 'New Room'
    
    @api.depends('current_agreement_id', 'current_agreement_id.rent_amount', 'rent_amount')
    def _compute_current_rent(self):
        """Compute current rent from active agreement or base rent"""
        for record in self:
            if record.current_agreement_id and record.current_agreement_id.state == 'active':
                # Use rent from active agreement
                record.current_rent = record.current_agreement_id.rent_amount
            else:
                # Use base rent from room
                record.current_rent = record.rent_amount
    
    @api.depends('status')
    def _compute_availability(self):
        for record in self:
            record.is_available = record.status in ['vacant', 'booked']
    
    @api.depends('status', 'current_agreement_id.end_date')
    def _compute_days_vacant(self):
        for record in self:
            if record.status == 'vacant':
                if record.current_agreement_id and record.current_agreement_id.end_date:
                    delta = fields.Date.today() - record.current_agreement_id.end_date
                    record.days_vacant = delta.days
                else:
                    record.days_vacant = 0
            else:
                record.days_vacant = 0
    
    def _compute_financial_stats(self):
        for record in self:
            collections = self.env['property.collection'].search([('room_id', '=', record.id), ('active', '=', True)])
            record.total_collected = sum(collections.mapped('amount_collected'))
            record.last_collection_date = max(collections.mapped('date')) if collections else False
            
            # Calculate pending amount based on current agreement
            if record.current_agreement_id and record.status == 'occupied':
                # This would need more complex logic based on payment schedule
                record.pending_amount = 0  # Simplified for now
            else:
                record.pending_amount = 0
    
    def _compute_tenant_financials(self):
        """Compute security deposit and outstanding dues for current tenant"""
        for record in self:
            if record.current_agreement_id:
                record.security_deposit = record.current_agreement_id.deposit_amount
            else:
                record.security_deposit = 0
            
            if record.current_tenant_id:
                # Get outstanding dues for current tenant
                outstanding_dues = self.env['property.outstanding.dues'].search([
                    ('tenant_id', '=', record.current_tenant_id.id),
                    ('agreement_id', '=', record.current_agreement_id.id if record.current_agreement_id else False)
                ], limit=1)
                record.outstanding_amount = outstanding_dues.outstanding_balance if outstanding_dues else 0
            else:
                record.outstanding_amount = 0
    
    def _compute_current_occupants(self):
        """Compute occupants for current agreement"""
        for record in self:
            if record.current_agreement_id:
                record.current_occupants_ids = record.current_agreement_id.occupant_ids
                record.occupants_count = len(record.current_agreement_id.occupant_ids)
            else:
                record.current_occupants_ids = False
                record.occupants_count = 0
    
    @api.constrains('property_id', 'flat_id', 'room_number')
    def _check_room_number_unique(self):
        for record in self:
            if record.flat_id and record.room_number:
                existing = self.search([
                    ('flat_id', '=', record.flat_id.id),
                    ('room_number', '=', record.room_number),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Room number must be unique within a flat!'))
    
    @api.onchange('flat_id')
    def _onchange_flat_id(self):
        if self.flat_id:
            self.property_id = self.flat_id.property_id
    
    @api.onchange('room_type_id')
    def _onchange_room_type_id(self):
        if self.room_type_id:
            # self.rent_amount = self.room_type_id.default_rent
            # self.deposit_amount = self.room_type_id.default_deposit
            self.has_private_bathroom = self.room_type_id.has_private_bathroom
    
    def action_book_room(self):
        self.write({'status': 'booked'})
        
    def action_occupy_room(self):
        self.write({'status': 'occupied'})
        
    def action_vacate_room(self):
        self.write({
            'status': 'vacant',
            'current_tenant_id': False,
            'current_agreement_id': False,
        })
        
    def action_maintenance(self):
        self.write({'status': 'maintenance'})
    
    def action_view_collections(self):
        return {
            'name': _('Room Collections'),
            'view_mode': 'list,form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'domain': [('room_id', '=', self.id), ('active', '=', True)],
            'context': {'default_room_id': self.id, 'default_property_id': self.property_id.id}
        }
    
    def action_create_agreement(self):
        return {
            'name': _('Create Agreement'),
            'view_mode': 'form',
            'res_model': 'property.agreement',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_room_id': self.id,
                'default_property_id': self.property_id.id,
                'default_rent_amount': self.rent_amount,
                'default_deposit_amount': self.deposit_amount,
            }
        }
    
    def write(self, vals):
        """Override write to invalidate parent computed fields and auto-create agreements"""
        # Critical fields that should not be modified when room has active agreement
        critical_fields = ['rent_amount', 'parking_charges', 'deposit_amount', 'room_type_id']
        
        # Check if trying to modify critical fields on rooms with active agreements
        if any(field in vals for field in critical_fields):
            rooms_with_active_agreement = self.filtered(
                lambda r: r.current_agreement_id and r.current_agreement_id.state == 'active'
            )
            if rooms_with_active_agreement:
                raise ValidationError(_(
                    'Cannot modify rent amount, parking charges, deposit amount, or room type '
                    'for rooms with active agreements! '
                    'Please terminate the agreement first or modify the agreement directly.'
                ))
        
        # Auto-create agreement when tenant is assigned to room
        # BUT only if we're not also setting current_agreement_id (which means agreement already exists)
        if 'current_tenant_id' in vals and vals['current_tenant_id'] and 'current_agreement_id' not in vals:
            for record in self:
                # Check if tenant already has active agreement for this room
                existing_agreement = self.env['property.agreement'].search([
                    ('tenant_id', '=', vals['current_tenant_id']),
                    ('room_id', '=', record.id),
                    ('state', '=', 'active')
                ], limit=1)
                
                if not existing_agreement:
                    # Create new agreement
                    tenant = self.env['property.tenant'].browse(vals['current_tenant_id'])
                    from datetime import date
                    from dateutil.relativedelta import relativedelta
                    
                    start_date = date.today()
                    end_date = start_date + relativedelta(years=1)
                    
                    # Calculate total extra charges from room
                    extra_charges = (record.cleaning_charges or 0) + \
                                  (record.extra_person_charges or 0) + \
                                  (record.maintenance_charges or 0) + \
                                  (record.utility_charges or 0)
                    
                    agreement_vals = {
                        'tenant_id': tenant.id,
                        'room_id': record.id,
                        'start_date': start_date,
                        'end_date': end_date,
                        'rent_amount': record.rent_amount,
                        'deposit_amount': record.deposit_amount,
                        'parking_charges': record.parking_charges,
                        'parking_deposit': record.parking_deposit,
                        'extra_charges': extra_charges,
                        'state': 'active',
                        'auto_generate_invoices': True,
                        'auto_post_invoices': False,
                        'invoice_day': 1,
                    }
                    
                    new_agreement = self.env['property.agreement'].create(agreement_vals)
                    vals['current_agreement_id'] = new_agreement.id
                    vals['status'] = 'occupied'
        
        result = super().write(vals)
        
        # Fields that affect flat's computed statistics
        fields_affecting_flat = [
            'rent_amount', 'status', 'current_tenant_id', 'current_agreement_id',
            'parking_charges', 'active'
        ]
        
        # Check if any of the critical fields were changed
        if any(field in vals for field in fields_affecting_flat):
            # Invalidate flat computed fields
            flats_to_recompute = self.mapped('flat_id')
            if flats_to_recompute:
                # Force recomputation of flat stats
                flats_to_recompute._compute_rooms_count()
                flats_to_recompute._compute_room_stats()
                flats_to_recompute._compute_financial()
                flats_to_recompute._compute_state()
                flats_to_recompute._compute_financial_summary()
            
            # Invalidate property computed fields
            properties_to_recompute = self.mapped('property_id')
            if properties_to_recompute:
                # Force recomputation of property stats
                properties_to_recompute._compute_total_flats()
                properties_to_recompute._compute_total_rooms()
                properties_to_recompute._compute_room_stats()
                properties_to_recompute._compute_financial_summary()
        
        return result
