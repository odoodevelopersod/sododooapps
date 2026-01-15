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
from datetime import datetime, timedelta


class PropertyAgreement(models.Model):
    _name = 'property.agreement'
    _description = 'Rental Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char('Agreement Reference', compute='_compute_name', store=True)
    
    # Relations
    tenant_id = fields.Many2one('property.tenant', 'Tenant', required=True, tracking=True)
    room_id = fields.Many2one('property.room', 'Room', required=True, tracking=True)
    property_id = fields.Many2one(related='room_id.property_id', string='Property', store=True)
    agent_id = fields.Many2one('res.partner', 'Agent', 
                              domain=[('is_company', '=', False), 
                                      '|', ('category_id.name', 'in', ['Property Agent', 'Rental Agent', 'Sales Agent']), 
                                      ('function', 'ilike', 'agent')],
                              help="Agent responsible for this agreement", tracking=True)
    
    # Other Charges
    other_charges_ids = fields.One2many('property.agreement.charges', 'agreement_id', 'Other Charges')
    
    # Occupants
    occupant_ids = fields.One2many('property.occupant', 'agreement_id', 'Occupants')
    occupants_count = fields.Integer('Total Occupants', compute='_compute_occupants_count', store=True)
    occupants_names = fields.Char('Occupants', compute='_compute_occupants_names', store=True)
    primary_occupant_id = fields.Many2one('property.occupant', 'Primary Occupant', 
                                         compute='_compute_primary_occupant', store=True)
    
    # Dummy fields to avoid view validation error during upgrade
    charge_id = fields.Many2one('property.other.charges', 'Dummy Charge', help="Temporary field for view validation")
    charge_name = fields.Char('Dummy Charge Name', help="Temporary field for view validation")
    charge_type = fields.Char('Dummy Charge Type', help="Temporary field for view validation")
    default_amount = fields.Monetary('Dummy Default Amount', currency_field='currency_id', help="Temporary field for view validation")
    custom_amount = fields.Boolean('Dummy Custom Amount', help="Temporary field for view validation")
    amount = fields.Monetary('Dummy Amount', currency_field='currency_id', help="Temporary field for view validation")
    # Note: start_date, end_date, and active already exist in the model, so no need to add them as dummies
    
    # Dates
    start_date = fields.Date('Start Date', required=True, tracking=True)
    end_date = fields.Date('End Date', required=True, tracking=True)
    notice_period_days = fields.Integer('Notice Period (Days)', default=30)
    
    # Financial Terms
    rent_amount = fields.Monetary('Monthly Rent', required=True, currency_field='currency_id', tracking=True)
    deposit_amount = fields.Monetary('Security Deposit', currency_field='currency_id', tracking=True)
    token_amount = fields.Monetary('Token Money', currency_field='currency_id', default=0.0)
    parking_charges = fields.Monetary('Parking Charges', currency_field='currency_id', default=0.0)
    parking_remote_deposit = fields.Monetary('Parking Remote Deposit', currency_field='currency_id', default=0.0)
    
    # Other Charges (moved from above)
    # other_charges_ids = fields.One2many('property.agreement.charges', 'agreement_id', 'Other Charges') # This field was already defined above, keeping it there.

    # Opening Balance
    opening_balance = fields.Monetary('Opening Balance', currency_field='currency_id', default=0.0,
                                     help="Any outstanding balance from previous agreement or external sources")
    opening_balance_recorded = fields.Boolean('Opening Balance Recorded', default=False, copy=False,
                                              help="Tracks if opening balance has been added to statement")

    invoice_ids = fields.One2many('account.move', 'agreement_id', 'Invoices')
    invoices_count = fields.Integer('Invoices Count', compute='_compute_invoices_count',)

    def _compute_invoices_count(self):
        for agreement in self:
            active_invoices = agreement.invoice_ids.filtered('active')
            agreement.invoices_count = len(active_invoices.filtered(lambda inv: inv.move_type in ('out_invoice', 'out_refund')))

    def action_view_invoices(self):
        active_invoices = self.invoice_ids.filtered('active')
        return {
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', active_invoices.ids), ('move_type', 'in', ('out_invoice', 'out_refund'))],
        }

    # Payment Terms
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ], string='Payment Method', required=True, default='cash')
    
    payment_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Payment Frequency', required=True, default='monthly')
    
    payment_day = fields.Integer('Payment Day of Month', default=1, help="Day of month when rent is due")
    payment_terms = fields.Integer('Payment Terms (Days)', default=30, help="Number of days to pay invoice")
    
    # Invoicing Automation
    auto_generate_invoices = fields.Boolean('Auto Generate Invoices', default=True, 
                                          help="Automatically generate monthly invoices")
    auto_post_invoices = fields.Boolean('Auto Post Invoices', default=True,
                                      help="Automatically post generated invoices")
    invoice_day = fields.Integer('Invoice Generation Day', default=1, 
                               help="Day of month to generate invoice")
    advance_invoice_days = fields.Integer('Advance Invoice Days', default=5,
                                        help="Generate invoice X days before due date")
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Agreement Details
    agreement_type = fields.Selection([
        ('fixed', 'Fixed Term'),
        ('renewable', 'Auto-Renewable'),
        ('month_to_month', 'Month to Month'),
    ], string='Agreement Type', default='fixed')
    
    # Terms and Conditions
    terms_and_conditions = fields.Html('Terms and Conditions')
    special_conditions = fields.Text('Special Conditions')
    
    # Utilities & Inclusions
    electricity_included = fields.Boolean('Electricity Included')
    water_included = fields.Boolean('Water Included', default=True)
    gas_included = fields.Boolean('Gas Included')
    internet_included = fields.Boolean('Internet Included', default=True)
    parking_included = fields.Boolean('Parking Included')
    
    # Relations
    collection_ids = fields.One2many('property.collection', 'agreement_id', 'Collections')
    
    # Computed Fields
    duration_months = fields.Integer('Duration (Months)', compute='_compute_duration')
    days_remaining = fields.Integer('Days Remaining', compute='_compute_days_remaining')
    total_collected = fields.Monetary('Total Collected', compute='_compute_payment_stats', currency_field='currency_id')
    pending_amount = fields.Monetary('Pending Amount', compute='_compute_payment_stats', currency_field='currency_id')
    last_payment_date = fields.Date('Last Payment', compute='_compute_payment_stats')
    
    # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Documents
    agreement_document = fields.Binary('Agreement Document')
    agreement_filename = fields.Char('Agreement Filename')
    
    @api.depends('tenant_id', 'room_id', 'start_date')
    def _compute_name(self):
        for record in self:
            if record.tenant_id and record.room_id and record.start_date:
                record.name = f"AGR/{record.tenant_id.name}/{record.room_id.name}/{record.start_date.strftime('%Y%m%d')}"
            else:
                record.name = 'New Agreement'
    
    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_months = round(delta.days / 30)
            else:
                record.duration_months = 0
    
    @api.depends('end_date')
    def _compute_days_remaining(self):
        today = fields.Date.today()
        for record in self:
            if record.end_date and record.state == 'active':
                delta = record.end_date - today
                record.days_remaining = delta.days
            else:
                record.days_remaining = 0
    
    @api.depends('collection_ids.amount_collected', 'collection_ids.active', 'start_date')
    def _compute_payment_stats(self):
        for record in self:
            active_collections = record.collection_ids.filtered('active')
            record.total_collected = sum(active_collections.mapped('amount_collected'))
            record.last_payment_date = max(active_collections.mapped('date')) if active_collections else False
            
            # Calculate pending amount using whole complete months
            if record.state == 'active':
                from dateutil.relativedelta import relativedelta
                
                # Calculate complete months between start_date and today
                delta = relativedelta(fields.Date.today(), record.start_date)
                complete_months = delta.years * 12 + delta.months
                
                # Expected amount based on complete months only (no partial months)
                expected_amount = record.rent_amount * complete_months
                record.pending_amount = max(0, expected_amount - record.total_collected)
            else:
                record.pending_amount = 0
    
    @api.depends('occupant_ids')
    def _compute_occupants_count(self):
        for record in self:
            record.occupants_count = len(record.occupant_ids.filtered('active'))
    
    @api.depends('occupant_ids', 'occupant_ids.name', 'occupant_ids.active')
    def _compute_occupants_names(self):
        for record in self:
            active_occupants = record.occupant_ids.filtered('active')
            if active_occupants:
                names = ', '.join(active_occupants.mapped('name'))
                record.occupants_names = names
            else:
                record.occupants_names = False
    
    @api.depends('occupant_ids', 'occupant_ids.is_primary', 'occupant_ids.active')
    def _compute_primary_occupant(self):
        for record in self:
            primary = record.occupant_ids.filtered(lambda o: o.is_primary and o.active)
            record.primary_occupant_id = primary[0] if primary else False
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError(_('End date must be after start date!'))
    
    @api.constrains('room_id', 'start_date', 'end_date')
    def _check_room_availability(self):
        for record in self:
            if record.room_id and record.start_date and record.end_date:
                # Check for overlapping agreements
                # Two date ranges overlap if: start1 < end2 AND start2 < end1
                overlapping = self.search([
                    ('room_id', '=', record.room_id.id),
                    ('state', 'in', ['active', 'draft']),
                    ('id', '!=', record.id),
                    ('start_date', '<', record.end_date),
                    ('end_date', '>', record.start_date),
                ])
                if overlapping:
                    raise ValidationError(_(
                        'Room is already rented during this period! '
                        'Conflicting agreement: %s (from %s to %s)'
                    ) % (overlapping[0].name, overlapping[0].start_date, overlapping[0].end_date))
    
    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.rent_amount = self.room_id.rent_amount
            self.deposit_amount = self.room_id.deposit_amount
            self.parking_charges = self.room_id.parking_charges
            # Note: parking_remote_deposit doesn't exist on room model
            self.property_id = self.room_id.property_id

    @api.onchange('tenant_id')
    def _onchange_tenant_id(self):
        if self.tenant_id:
            self.payment_method = self.tenant_id.payment_method
    
    @api.onchange('agent_id')
    def _onchange_agent_id(self):
        """Update any agent-specific defaults when agent is selected"""
        if self.agent_id:
            # You can add agent-specific logic here
            # For example, set default payment terms based on agent preferences
            pass
    
    def action_activate(self):
        """Activate agreement and create initial statement entries"""
        for record in self:
            # Update room status
            record.room_id.write({
                'status': 'occupied',
                'current_tenant_id': record.tenant_id.id,
                'current_agreement_id': record.id,
            })
            
            # Update tenant status
            record.tenant_id.write({
                'status': 'active',
                'current_room_id': record.room_id.id,
                'current_agreement_id': record.id,
            })
            
            record.write({'state': 'active'})
            
            # Create initial statement entries for dues
            record._create_initial_statement_entries()
            
            # Create monthly invoice reference
            record._create_monthly_invoice_reference()
    
    def _create_initial_statement_entries(self):
        """Create initial statement entries for agreement dues"""
        self.ensure_one()
        
        statement_obj = self.env['property.statement']
        today = fields.Date.today()
        
        # 1. Create entry for opening balance (if > 0 and not already recorded)
        if self.opening_balance > 0 and not self.opening_balance_recorded:
            statement_obj.create({
                'tenant_id': self.tenant_id.id,
                'agreement_id': self.id,
                'transaction_date': today,
                'reference': f'{self.name}/OPENING',
                'description': f'Opening balance for agreement {self.name}',
                'transaction_type': 'outstanding',
                'debit_amount': self.opening_balance,
                'credit_amount': 0.0,
            })
            # Mark as recorded so it doesn't get created again
            self.opening_balance_recorded = True
        
        # 2. Create entry for security deposit (if not paid)
        if self.deposit_amount > 0:
            statement_obj.create({
                'tenant_id': self.tenant_id.id,
                'agreement_id': self.id,
                'transaction_date': today,
                'reference': f'{self.name}/DEPOSIT',
                'description': f'Security deposit for agreement {self.name}',
                'transaction_type': 'deposit',
                'debit_amount': self.deposit_amount,
                'credit_amount': 0.0,
            })
        
        # 3. Create entry for parking charges (if > 0)
        if self.parking_charges > 0:
            statement_obj.create({
                'tenant_id': self.tenant_id.id,
                'agreement_id': self.id,
                'transaction_date': today,
                'reference': f'{self.name}/PARKING',
                'description': f'Parking charges for agreement {self.name}',
                'transaction_type': 'parking',
                'debit_amount': self.parking_charges,
                'credit_amount': 0.0,
            })
        
        # 4. Create entries for other charges (if > 0)
        for charge in self.other_charges_ids:
            if charge.amount > 0:
                statement_obj.create({
                    'tenant_id': self.tenant_id.id,
                    'agreement_id': self.id,
                    'transaction_date': today,
                    'reference': f'{self.name}/CHARGE/{charge.charge_id.name}',
                    'description': f'{charge.charge_id.name} for agreement {self.name}',
                    'transaction_type': 'other',
                    'debit_amount': charge.amount,
                    'credit_amount': 0.0,
                })
        
        # Recalculate running balances for this tenant
        tenant_statements = statement_obj.search([
            ('tenant_id', '=', self.tenant_id.id)
        ], order='transaction_date asc, id asc')
        tenant_statements._compute_running_balance()
    
    def action_terminate(self):
        """Regular termination - just marks agreement as terminated"""
        for record in self:
            # Update room status
            record.room_id.write({
                'status': 'vacant',
                'current_tenant_id': False,
                'current_agreement_id': False,
            })
            
            # Update tenant status
            record.tenant_id.write({
                'current_room_id': False,
            })
            
            record.write({'state': 'terminated'})
        return True
    
    def action_clean_and_terminate(self):
        """Delete all related data and terminate the agreement"""
        self.ensure_one()
        
        # Return confirmation wizard
        return {
            'name': _('Confirm Clean & Terminate'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.agreement.clean.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_agreement_id': self.id,
                'default_agreement_name': self.name,
            }
        }
    
    def action_renew(self):
        return {
            'name': _('Renew Agreement'),
            'view_mode': 'form',
            'res_model': 'property.agreement',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_tenant_id': self.tenant_id.id,
                'default_room_id': self.room_id.id,
                'default_rent_amount': self.rent_amount,
                'default_deposit_amount': self.deposit_amount,
                'default_start_date': self.end_date + timedelta(days=1),
                'default_end_date': self.end_date + timedelta(days=365),
            }
        }
    
    def _create_monthly_invoice_reference(self):
        """Create monthly invoice reference for the agreement (Community Edition)"""
        self.ensure_one()
        
        # Create a simple invoice reference without actual accounting integration
        invoice_ref = f"INV/{self.tenant_id.name[:10]}/{fields.Date.today().strftime('%Y%m%d')}"
        
        # You can extend this to create a simple invoice record in a custom model
        # or integrate with accounting module if available
        
        return invoice_ref
    
    @api.model
    def _cron_check_expiring_agreements(self):
        """Cron job to check for expiring agreements"""
        expiring_date = fields.Date.today() + timedelta(days=30)
        expiring_agreements = self.search([
            ('state', '=', 'active'),
            ('end_date', '<=', expiring_date),
        ])
        
        for agreement in expiring_agreements:
            # Send notification or create activity
            agreement.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Agreement expiring for {agreement.tenant_id.name}',
                note=f'Agreement for room {agreement.room_id.name} expires on {agreement.end_date}',
                user_id=agreement.room_id.property_id.manager_id.id,
            )
    
    def action_view_agent_agreements(self):
        """View all agreements for the selected agent"""
        if not self.agent_id:
            return
        
        return {
            'name': f'Agreements - {self.agent_id.name}',
            'view_mode': 'list,form',
            'res_model': 'property.agreement',
            'type': 'ir.actions.act_window',
            'domain': [('agent_id', '=', self.agent_id.id)],
            'context': {'default_agent_id': self.agent_id.id},
        }
    
    def write(self, vals):
        """Override write to prevent modification of critical fields when agreement is active"""
        # Check if any record is active and trying to modify critical fields
        critical_fields = [
            'tenant_id', 'room_id', 'start_date', 'end_date',
            'rent_amount', 'deposit_amount', 'parking_charges', 'parking_deposit'
        ]
        
        # Check if trying to archive active agreement
        if 'active' in vals and not vals['active']:
            active_agreements = self.filtered(lambda a: a.state == 'active')
            if active_agreements:
                raise ValidationError(_(
                    'Cannot archive active agreements! '
                    'Please terminate the agreement first.'
                ))
        
        # Check if trying to modify critical fields on active agreements
        for field in critical_fields:
            if field in vals:
                active_agreements = self.filtered(lambda a: a.state == 'active')
                if active_agreements:
                    raise ValidationError(_(
                        'Cannot modify %s of active agreements! '
                        'Please terminate the agreement first if you need to make changes.'
                    ) % field.replace('_', ' ').title())
        
        result = super().write(vals)
        
        # If active field is being changed, invalidate tenant computed fields
        if 'active' in vals:
            tenants_to_recompute = self.mapped('tenant_id')
            if tenants_to_recompute:
                # Force recomputation of tenant stats
                tenants_to_recompute._compute_agreement_stats()
        
        return result
    
    @api.model
    def cron_recompute_outstanding_dues(self):
        """Cron job to recompute all outstanding dues - useful after code changes"""
        # Recompute all active agreements
        agreements = self.search([('state', '=', 'active')])
        if agreements:
            agreements._compute_payment_stats()
        
        # Recompute all flats
        flats = self.env['property.flat'].search([])
        if flats:
            flats._compute_financial_summary()
        
        return True
    
    def unlink(self):
        """Override unlink to prevent deletion of active agreements"""
        active_agreements = self.filtered(lambda a: a.state == 'active')
        if active_agreements:
            raise ValidationError(_(
                'Cannot delete active agreements! '
                'Please terminate the agreement first.'
            ))
        return super().unlink()
