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

class ResPartner(models.Model):
    _inherit = 'res.partner'
    tenant_id = fields.Many2one('property.tenant', string='Tenant', help="Link to the tenant record if this partner is a tenant.")

class PropertyTenant(models.Model):
    _name = 'property.tenant'
    _description = 'Property Tenant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    # Basic Information
    name = fields.Char('Full Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', 'Related Contact', ondelete='cascade')
    mobile = fields.Char('Mobile Number', related="partner_id.mobile", store=True, readonly=False, required=True, tracking=True)
    phone = fields.Char('Phone Number', related="partner_id.phone", store=True, readonly=False, required=True, tracking=True)
    email = fields.Char('Email', related="partner_id.email", store=True, readonly=False, required=True, tracking=True)
    nationality = fields.Many2one('res.country', 'Nationality', related="partner_id.country_id", store=True, readonly=False)

    # Identification
    id_passport = fields.Char('ID/Passport Number', required=True, tracking=True)
    id_type = fields.Selection([
        ('emirates_id', 'Emirates ID'),
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('other', 'Other'),
    ], string='ID Type', required=True, default='emirates_id')
    
    # Additional Contact Information
    emergency_contact_name = fields.Char('Emergency Contact Name')
    emergency_contact_phone = fields.Char('Emergency Contact Phone')
    emergency_contact_relation = fields.Char('Relation')
    
    # Professional Information
    company_name = fields.Char('Company Name')
    job_title = fields.Char('Job Title')
    work_phone = fields.Char('Work Phone')
    monthly_income = fields.Monetary('Monthly Income', currency_field='currency_id')
    
    # Preferences
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ], string='Preferred Payment Method', default='cash')
    
    preferred_language = fields.Selection([
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('ur', 'Urdu'),
        ('hi', 'Hindi'),
        ('fr', 'French'),
        ('other', 'Other'),
    ], string='Preferred Language', default='en')
    
    # Status
    status = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active Tenant'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='prospect', tracking=True)
    
    # Relations
    partner_id = fields.Many2one('res.partner', 'Contact', ondelete='cascade')
    current_room_id = fields.Many2one('property.room', 'Current Room')
    current_room_number = fields.Char('Current Room Number', compute='_compute_current_room_info', store=True)
    current_flat_id = fields.Many2one('property.flat', 'Current Flat', compute='_compute_current_location', store=True)
    current_property_id = fields.Many2one('property.property', 'Current Property', compute='_compute_current_location', store=True)
    current_agreement_id = fields.Many2one('property.agreement', 'Current Agreement', compute='_compute_current_agreement')
    agreement_ids = fields.One2many('property.agreement', 'tenant_id', 'Agreements')
    collection_ids = fields.One2many('property.collection', 'tenant_id', 'Collections')
    
    # Documents
    document_ids = fields.One2many('ir.attachment', 'res_id', 'Documents',
                                   domain=[('res_model', '=', 'property.tenant')])
    
    # Computed Fields
    active_agreements_count = fields.Integer('Active Agreements', compute='_compute_agreement_stats')
    total_agreements_count = fields.Integer('Total Agreements', compute='_compute_agreement_stats')
    total_paid = fields.Monetary('Total Paid', compute='_compute_payment_stats', currency_field='currency_id')
    last_payment_date = fields.Date('Last Payment', compute='_compute_payment_stats')
    
    # Outstanding Dues
    total_outstanding_dues = fields.Monetary('Total Outstanding', currency_field='currency_id', 
                                            compute='_compute_outstanding_dues', store=True)
    rent_outstanding = fields.Monetary('Rent Outstanding', currency_field='currency_id', 
                                      compute='_compute_outstanding_dues', store=True)
    deposit_outstanding = fields.Monetary('Deposit Outstanding', currency_field='currency_id', 
                                         compute='_compute_outstanding_dues', store=True)
    parking_outstanding = fields.Monetary('Parking Outstanding', currency_field='currency_id', 
                                         compute='_compute_outstanding_dues', store=True)
    outstanding_status = fields.Selection([
        ('current', 'Current'),
        ('overdue', 'Overdue'),
        ('critical', 'Critical'),
    ], string='Outstanding Status', compute='_compute_outstanding_dues', store=True)
    
    # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Additional Fields
    notes = fields.Text('Notes')
    date_joined = fields.Date('Date Joined', default=fields.Date.today)
    
    # Image
    image = fields.Image('Photo', max_width=1920, max_height=1920)
    
    @api.depends('current_room_id', 'current_room_id.flat_id', 'current_room_id.property_id')
    def _compute_current_location(self):
        for record in self:
            if record.current_room_id:
                record.current_flat_id = record.current_room_id.flat_id
                record.current_property_id = record.current_room_id.property_id
            else:
                record.current_flat_id = False
                record.current_property_id = False
    
    @api.depends('current_room_id', 'current_room_id.room_number', 'current_room_id.name')
    def _compute_current_room_info(self):
        for record in self:
            if record.current_room_id:
                # Show full room details: Property-Flat-Room format
                record.current_room_number = record.current_room_id.name or f"{record.current_room_id.room_number}"
            else:
                record.current_room_number = ""
    
    @api.depends('agreement_ids', 'agreement_ids.state', 'agreement_ids.start_date', 'agreement_ids.end_date')
    def _compute_current_agreement(self):
        """Compute the current active agreement for the tenant"""
        for record in self:
            # Find active agreements ordered by start date (most recent first)
            current_agreement = record.agreement_ids.filtered(
                lambda a: a.state == 'active'
            ).sorted('start_date', reverse=True)
            
            # Set the most recent active agreement as current
            record.current_agreement_id = current_agreement[0] if current_agreement else False
    
    @api.depends('agreement_ids.state', 'agreement_ids.active')
    def _compute_agreement_stats(self):
        for record in self:
            active_agreements = record.agreement_ids.filtered('active')
            record.total_agreements_count = len(active_agreements)
            record.active_agreements_count = len(active_agreements.filtered(lambda a: a.state == 'active'))
    
    @api.depends('collection_ids.amount_collected', 'collection_ids.active')
    def _compute_payment_stats(self):
        for record in self:
            active_collections = record.collection_ids.filtered('active')
            record.total_paid = sum(active_collections.mapped('amount_collected'))
            if active_collections:
                record.last_payment_date = max(active_collections.mapped('date'))
            else:
                record.last_payment_date = False
    
    @api.depends('current_agreement_id', 'collection_ids.amount_collected', 'collection_ids.date', 'collection_ids.active')
    def _compute_outstanding_dues(self):
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        
        for record in self:
            if not record.current_agreement_id or record.current_agreement_id.state != 'active':
                record.total_outstanding_dues = 0
                record.rent_outstanding = 0
                record.deposit_outstanding = 0
                record.outstanding_status = 'current'
                continue
            
            agreement = record.current_agreement_id
            today = fields.Date.today()
            
            # Calculate rent outstanding using complete months only (matching agreement logic)
            start_date = agreement.start_date
            monthly_rent = agreement.rent_amount
            
            # Calculate COMPLETE months only (no partial months)
            delta = relativedelta(today, start_date)
            complete_months = delta.years * 12 + delta.months
            
            expected_rent = monthly_rent * complete_months if complete_months > 0 else 0
            
            # Calculate total rent collected
            active_collections = record.collection_ids.filtered('active')
            rent_collections = active_collections.filtered(lambda c: c.collection_type == 'rent')
            total_rent_collected = sum(rent_collections.mapped('amount_collected'))
            
            rent_outstanding = max(0, expected_rent - total_rent_collected)
            
            # Calculate deposit outstanding
            expected_deposit = agreement.deposit_amount
            deposit_collections = active_collections.filtered(lambda c: c.collection_type == 'deposit')
            total_deposit_collected = sum(deposit_collections.mapped('amount_collected'))
            deposit_outstanding = max(0, expected_deposit - total_deposit_collected)
            
            # Calculate parking outstanding
            expected_parking = agreement.parking_charges if hasattr(agreement, 'parking_charges') else 0
            parking_collections = active_collections.filtered(lambda c: c.collection_type == 'parking')
            total_parking_collected = sum(parking_collections.mapped('amount_collected'))
            parking_outstanding = max(0, expected_parking - total_parking_collected)
            
            # Total outstanding
            total_outstanding = rent_outstanding + deposit_outstanding + parking_outstanding
            
            # Calculate status based on last payment
            last_payment_date = max(active_collections.mapped('date')) if active_collections else agreement.start_date
            days_overdue = (today - last_payment_date).days if last_payment_date else 0
            
            if total_outstanding <= 0:
                outstanding_status = 'current'
            elif days_overdue <= 90:
                outstanding_status = 'overdue'
            else:
                outstanding_status = 'critical'
            
            record.total_outstanding_dues = total_outstanding
            record.rent_outstanding = rent_outstanding
            record.deposit_outstanding = deposit_outstanding
            record.parking_outstanding = parking_outstanding
            record.outstanding_status = outstanding_status
    # @api.depends('current_agreement_id', 'collection_ids.amount_collected', 'collection_ids.date', 'collection_ids.active')
    # def _compute_outstanding_dues(self):
    #     from datetime import datetime
    #     from dateutil.relativedelta import relativedelta
    #     
    #     for record in self:
    #         if not record.current_agreement_id or record.current_agreement_id.state != 'active':
    #             record.total_outstanding_dues = 0
    #             record.rent_outstanding = 0
    #             record.deposit_outstanding = 0
    #             record.outstanding_status = 'current'
    #             continue
    #         
    #         agreement = record.current_agreement_id
    #         today = fields.Date.today()
    #         
    #         # Calculate rent outstanding
    #         start_date = agreement.start_date
    #         monthly_rent = agreement.rent_amount
    #         
    #         # Calculate expected rent based on months passed
    #         months_passed = relativedelta(today, start_date).months + (relativedelta(today, start_date).years * 12)
    #         if today.day >= agreement.payment_day:
    #             months_passed += 1  # Include current month if past due date
    #         
    #         expected_rent = monthly_rent * months_passed if months_passed > 0 else 0
    #         
    #         # Calculate total rent collected
    #         active_collections = record.collection_ids.filtered('active')
    #         rent_collections = active_collections.filtered(lambda c: c.collection_type == 'rent')
    #         total_rent_collected = sum(rent_collections.mapped('amount_collected'))
    #         
    #         rent_outstanding = max(0, expected_rent - total_rent_collected)
    #         
    #         # Calculate deposit outstanding
    #         expected_deposit = agreement.deposit_amount
    #         deposit_collections = active_collections.filtered(lambda c: c.collection_type == 'deposit')
    #         total_deposit_collected = sum(deposit_collections.mapped('amount_collected'))
    #         deposit_outstanding = max(0, expected_deposit - total_deposit_collected)
    #         
    #         # Total outstanding
    #         total_outstanding = rent_outstanding + deposit_outstanding
    #         
    #         # Calculate status based on last payment
    #         last_payment_date = max(active_collections.mapped('date')) if active_collections else agreement.start_date
    #         days_overdue = (today - last_payment_date).days if last_payment_date else 0
    #         
    #         if total_outstanding <= 0:
    #             outstanding_status = 'current'
    #         elif days_overdue <= 30:
    #             outstanding_status = 'overdue_30'
    #         elif days_overdue <= 60:
    #             outstanding_status = 'overdue_60'
    #         elif days_overdue <= 90:
    #             outstanding_status = 'overdue_90'
    #         elif days_overdue <= 180:
    #             outstanding_status = 'overdue_90plus'
    #         else:
    #             outstanding_status = 'critical'
    #         
    #         record.total_outstanding_dues = total_outstanding
    #         record.rent_outstanding = rent_outstanding
    #         record.deposit_outstanding = deposit_outstanding
    #         record.outstanding_status = outstanding_status
    
    def write(self, vals):
        # Update corresponding res.partner
        if self.partner_id:
            partner_vals = {}
            if 'name' in vals:
                partner_vals['name'] = vals['name']
            if 'mobile' in vals:
                partner_vals['mobile'] = vals['mobile']
            if 'email' in vals:
                partner_vals['email'] = vals['email']
            
            if partner_vals:
                self.partner_id.write(partner_vals)
        
        return super().write(vals)
    
    @api.constrains('id_passport')
    def _check_id_passport_unique(self):
        for record in self:
            if record.id_passport:
                existing = self.search([
                    ('id_passport', '=', record.id_passport),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('ID/Passport number must be unique!'))
    
    @api.constrains('mobile')
    def _check_mobile_unique(self):
        for record in self:
            if record.mobile:
                existing = self.search([
                    ('mobile', '=', record.mobile),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_('Mobile number must be unique!'))
    
    def action_activate(self):
        self.write({'status': 'active'})
        
    def action_deactivate(self):
        self.write({'status': 'inactive'})
        
    def action_blacklist(self):
        self.write({'status': 'blacklisted'})
    
    def action_view_agreements(self):
        return {
            'name': _('Tenant Agreements'),
            'view_mode': 'list,form',
            'res_model': 'property.agreement',
            'type': 'ir.actions.act_window',
            'domain': [('tenant_id', '=', self.id), ('active', '=', True)],
            'context': {'default_tenant_id': self.id}
        }
    
    # @api.model
    # def create(self, vals):
    #     # Create or link to partner
    #     if not vals.get('partner_id'):
    #         partner_vals = {
    #             'name': vals.get('name'),
    #             'phone': vals.get('mobile'),
    #             'email': vals.get('email'),
    #             'is_company': False,
    #             'customer_rank': 1,
    #         }
    #         partner = self.env['res.partner'].create(partner_vals)
    #         vals['partner_id'] = partner.id
        
    #     return super(PropertyTenant, self).create(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        # Create corresponding res.partner
        for vals in vals_list:
            if not vals.get('partner_id'):
                partner_vals = {
                    'name': vals.get('name'),
                    'mobile': vals.get('mobile'),
                    'email': vals.get('email'),
                    'is_company': False,
                    'customer_rank': 1,
                    'category_id': [(4, self.env.ref('property_management_lite.partner_category_tenant').id)],
            }
            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_id'] = partner.id
        recs = super().create(vals_list)
        for rec in recs:
            if rec.partner_id:
                rec.partner_id.tenant_id = rec.id
        return recs
    
    def write(self, vals):
        # Sync changes to partner
        result = super(PropertyTenant, self).write(vals)
        
        for record in self:
            if record.partner_id:
                partner_vals = {}
                if 'name' in vals:
                    partner_vals['name'] = vals['name']
                if 'mobile' in vals:
                    partner_vals['phone'] = vals['mobile']
                if 'email' in vals:
                    partner_vals['email'] = vals['email']
                
                if partner_vals:
                    record.partner_id.write(partner_vals)
        
        return result

    def action_view_collections(self):
        return {
            'name': _('Tenant Collections'),
            'view_mode': 'list,form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'domain': [('tenant_id', '=', self.id), ('active', '=', True)],
            'context': {'default_tenant_id': self.id}
        }
    
    def action_create_agreement(self):
        return {
            'name': _('Create Agreement'),
            'view_mode': 'form',
            'res_model': 'property.agreement',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_tenant_id': self.id}
        }
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.mobile})"
            result.append((record.id, name))
        return result
    
    def action_recalculate_statements(self):
        """Recalculate statement entries for this tenant"""
        self.ensure_one()
        
        # Get current agreement
        if not self.current_agreement_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Active Agreement'),
                    'message': _('This tenant has no active agreement.'),
                    'type': 'warning',
                }
            }
        
        agreement = self.current_agreement_id
        
        # Only delete INVOICE-based statements (not collection statements)
        # This preserves the link between collections and their statement entries
        invoice_statements = self.env['property.statement'].search([
            ('tenant_id', '=', self.id),
            ('transaction_type', 'in', ['invoice', 'rent', 'deposit', 'parking', 'other']),
            ('collection_id', '=', False)  # Only delete statements NOT linked to collections
        ])
        
        count_deleted = len(invoice_statements)
        invoice_statements.unlink()
        
        # Recreate invoice-based statements from agreement
        self.env['property.statement'].create_from_agreement(agreement)
        
        # Recreate missing collection statements for verified/collected/deposited collections
        collections_needing_statements = self.env['property.collection'].search([
            ('tenant_id', '=', self.id),
            ('status', 'in', ['collected', 'verified', 'deposited']),
            ('statement_id', '=', False)  # Collections missing statement entries
        ])
        
        count_collections_fixed = 0
        for collection in collections_needing_statements:
            try:
                statement = self.env['property.statement'].create_from_collection(collection)
                collection.statement_id = statement.id
                count_collections_fixed += 1
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Could not create statement for collection {collection.name}: {str(e)}")
        
        # Recalculate running balances for ALL statements
        all_statements = self.env['property.statement'].search([
            ('tenant_id', '=', self.id)
        ], order='transaction_date asc, id asc')
        all_statements._compute_running_balance()
        
        message = _('Recalculated %d invoice statements.') % count_deleted
        if count_collections_fixed > 0:
            message += _(' Recreated %d missing collection entries.') % count_collections_fixed
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
