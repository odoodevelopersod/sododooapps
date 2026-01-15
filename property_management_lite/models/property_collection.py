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


class PropertyCollection(models.Model):
    _name = 'property.collection'
    _description = 'Rent Collection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Collection Reference', compute='_compute_name', store=True)
    
    # Basic Information
    date = fields.Date('Collection Date', required=True, default=fields.Date.today, tracking=True)
    amount_collected = fields.Monetary('Amount Collected', required=True, currency_field='currency_id', tracking=True)
    
    # Relations
    tenant_id = fields.Many2one('property.tenant', 'Tenant', required=True, tracking=True)
    room_id = fields.Many2one('property.room', 'Room', required=True, tracking=True)
    property_id = fields.Many2one(related='room_id.property_id', string='Property', store=True, readonly=True)
    agreement_id = fields.Many2one('property.agreement', 'Agreement')
    other_charge_id = fields.Many2one('property.other.charges', 'Other Charge', 
                                     help="Select specific other charge when collection type is 'Other Charges'")
    
    # Payment Details
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
        ('card', 'Card Payment'),
    ], string='Payment Method', required=True, default='cash', tracking=True)
    
    reference_number = fields.Char('Reference Number', help="Cheque number, transaction ID, etc.")
    
    # Collection Details
    collection_type = fields.Selection([
        ('rent', 'Monthly Rent'),
        ('deposit', 'Security Deposit'),
        ('token', 'Token Money'),
        ('parking_charges', 'Parking Charges'),
        ('parking_deposit', 'Parking Remote Deposit'),
        ('other_charges', 'Other Charges'),
        ('extra', 'Extra Charges'),
        ('penalty', 'Late Payment Penalty'),
        ('maintenance', 'Maintenance Charges'),
        ('utility', 'Utility Bills'),
        ('outstanding', 'Outstanding Balance'),
        ('other', 'Other'),
    ], string='Collection Type', required=True, default='rent')
    
    period_from = fields.Date('Period From')
    period_to = fields.Date('Period To')
    
    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('collected', 'Collected'),
        ('verified', 'Verified'),
        ('deposited', 'Deposited'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='collected', tracking=True)
    
    # Additional Information
    notes = fields.Text('Notes')
    collected_by = fields.Many2one('res.users', 'Collected By', default=lambda self: self.env.user)
    verified_by = fields.Many2one('res.users', 'Verified By')
    verification_date = fields.Datetime('Verification Date')
    
    # Receipt Information
    receipt_number = fields.Char('Receipt Number')
    receipt_image = fields.Binary('Receipt Image')
    receipt_filename = fields.Char('Receipt Filename')
    
    # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Bank Information (for transfers)
    bank_id = fields.Many2one('res.bank', 'Bank')
    bank_account = fields.Char('Bank Account')
    
    # Late Payment
    due_date = fields.Date('Due Date')
    days_late = fields.Integer('Days Late', compute='_compute_days_late', store=True)
    late_fee = fields.Monetary('Late Fee', currency_field='currency_id')
    
    # Simple Invoice/Payment Reference (Community Edition)
    invoice_reference = fields.Char('Invoice Reference')
    payment_reference = fields.Char('Payment Reference')
    
    # Odoo Accounting Integration
    payment_id = fields.Many2one('account.payment', 'Payment', readonly=True, 
                                help="Linked payment record in Odoo accounting")
    matched_invoice_ids = fields.Many2many('account.move', 'collection_invoice_rel', 
                                          'collection_id', 'invoice_id',
                                          string='Matched Invoices', readonly=True,
                                          help="Invoices paid by this collection")
    
    @api.model
    def create(self, vals):
        print("iujhygt",self.tenant_id.agreement_ids.room_id)
        # Generate receipt number for new collections
        if not vals.get('receipt_number'):
            sequence = self.env['ir.sequence'].next_by_code('property.collection') or '/'
            vals['receipt_number'] = sequence
        
        # Set collected_by to current user if not set
        if not vals.get('collected_by'):
            vals['collected_by'] = self.env.user.id
        
        # Auto-populate room and agreement from tenant if not provided
        if vals.get('tenant_id') and not vals.get('room_id'):
            tenant = self.env['property.tenant'].browse(vals['tenant_id'])
            if tenant.current_room_id:
                vals['room_id'] = tenant.current_room_id.id
            if tenant.current_agreement_id and not vals.get('agreement_id'):
                vals['agreement_id'] = tenant.current_agreement_id.id
                # Auto-set amount if not provided
                if not vals.get('amount_collected') and vals.get('collection_type'):
                    if vals['collection_type'] == 'rent':
                        vals['amount_collected'] = tenant.current_agreement_id.rent_amount
                    elif vals['collection_type'] == 'deposit':
                        vals['amount_collected'] = tenant.current_agreement_id.deposit_amount
                    elif vals['collection_type'] == 'parking_charges':
                        vals['amount_collected'] = tenant.current_agreement_id.parking_charges
                    elif vals['collection_type'] == 'parking_deposit':
                        vals['amount_collected'] = tenant.current_agreement_id.parking_deposit
        
        # Auto-calculate rent period if not provided
        if (vals.get('collection_type') in ['rent', 'parking_charges'] and vals.get('date') and 
            not vals.get('period_from') and not vals.get('period_to')):
            
            from datetime import datetime
            if isinstance(vals['date'], str):
                collection_date = datetime.strptime(vals['date'], '%Y-%m-%d').date()
            else:
                collection_date = vals['date']
            
            year = collection_date.year
            month = collection_date.month
            
            # First day of the month
            period_from = collection_date.replace(day=1)
            
            # Last day of the month
            if month == 12:
                next_month = collection_date.replace(year=year + 1, month=1, day=1)
            else:
                next_month = collection_date.replace(month=month + 1, day=1)
            period_to = next_month - timedelta(days=1)
            
            vals['period_from'] = period_from
            vals['period_to'] = period_to
            
            # Set due date to last day of previous month
            if month == 1:
                due_date = collection_date.replace(year=year - 1, month=12, day=31)
            else:
                next_month_first = collection_date.replace(day=1)
                due_date = next_month_first - timedelta(days=1)
            vals['due_date'] = due_date
        
        collection = super().create(vals)
        
        # Auto-register payment against invoices if status is collected/verified
        if collection.status in ['collected', 'verified'] and not collection.payment_id:
            try:
                collection._register_payment_for_collection()
            except Exception as e:
                # Log error but don't block collection creation
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Could not register payment for collection {collection.name}: {str(e)}")
        
        return collection
    
    def write(self, vals):
        """Override write to invalidate related computed fields when active status changes"""
        
        # Handle cancellation - remove statement entry and reverse payment
        if 'status' in vals and vals['status'] == 'cancelled':
            for record in self:
                # Delete statement entry if exists
                if record.statement_id:
                    record.statement_id.unlink()
                
                # Cancel payment if exists
                if record.payment_id:
                    try:
                        # Set to draft first, then delete to avoid validation errors
                        if record.payment_id.state == 'posted':
                            record.payment_id.button_draft()
                        record.payment_id.unlink()
                    except Exception as e:
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f"Could not cancel payment for collection {record.name}: {str(e)}")
        
        # Handle verification - create statement and register payment
        if 'status' in vals and vals['status'] in ['collected', 'verified', 'deposited']:
            for record in self:
                # Create statement entry if doesn't exist
                if record.tenant_id and not record.statement_id:
                    try:
                        # Use savepoint to isolate constraint violations
                        with self.env.cr.savepoint():
                            statement = self.env['property.statement'].create_from_collection(record)
                            record.statement_id = statement.id
                    except Exception as e:
                        # Skip duplicates silently
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f"Could not create statement for collection {record.name}: {str(e)}")
                
                # Register payment if doesn't exist
                if not record.payment_id:
                    try:
                        record._register_payment_for_collection()
                    except Exception as e:
                        # Log error but don't block collection creation
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f"Could not register payment for collection {record.name}: {str(e)}")
        
        result = super(PropertyCollection, self).write(vals)
        
        # If active field is being changed, invalidate tenant and agreement computed fields
        if 'active' in vals:
            # Invalidate tenant computed fields
            tenants_to_recompute = self.mapped('tenant_id')
            if tenants_to_recompute:
                tenants_to_recompute._compute_payment_stats()
            
            # Invalidate agreement computed fields
            agreements_to_recompute = self.mapped('agreement_id')
            if agreements_to_recompute:
                agreements_to_recompute._compute_payment_stats()
            
            # Invalidate room computed fields
            rooms_to_recompute = self.mapped('room_id')
            if rooms_to_recompute:
                rooms_to_recompute._compute_payment_stats()
        
        return result

    @api.onchange('date', 'collection_type')
    def _onchange_date_collection_type(self):
        """Auto-calculate rent period based on collection date and type"""
        if self.date and self.collection_type in ['rent', 'parking_charges']:
            # Calculate period from 1st to last day of the collection month
            year = self.date.year
            month = self.date.month
            
            # First day of the month
            period_from = self.date.replace(day=1)
            
            # Last day of the month
            if month == 12:
                next_month = self.date.replace(year=year + 1, month=1, day=1)
            else:
                next_month = self.date.replace(month=month + 1, day=1)
            period_to = next_month - timedelta(days=1)
            
            self.period_from = period_from
            self.period_to = period_to
            
            # Set due date to last day of previous month for rent
            if month == 1:
                due_date = self.date.replace(year=year - 1, month=12, day=31)
            else:
                prev_month_last_day = self.date.replace(month=month - 1, day=1)
                if month - 1 == 12:
                    prev_month_last_day = prev_month_last_day.replace(year=year - 1, month=12)
                else:
                    prev_month_last_day = prev_month_last_day.replace(month=month - 1)
                # Get last day of previous month
                next_month_first = self.date.replace(day=1)
                due_date = next_month_first - timedelta(days=1)
            
            self.due_date = due_date
        elif self.collection_type not in ['rent', 'parking_charges']:
            # Clear period fields for non-rent/parking collections
            self.period_from = False
            self.period_to = False
            self.due_date = False
        
        # Clear other charge if collection type is not other_charges
        if self.collection_type != 'other_charges':
            self.other_charge_id = False
    
    @api.depends('tenant_id', 'room_id', 'date', 'collection_type', 'period_from', 'period_to')
    def _compute_name(self):
        for record in self:
            if record.tenant_id and record.room_id and record.date:
                date_str = record.date.strftime('%Y%m%d')
                tenant_name = record.tenant_id.name[:10]
                room_number = record.room_id.room_number
                
                # Include period information for rent collections
                if record.collection_type == 'rent' and record.period_from and record.period_to:
                    period_str = f"/{record.period_from.strftime('%m%Y')}"
                    record.name = f"COL/{date_str}/{tenant_name}/{room_number}{period_str}"
                else:
                    record.name = f"COL/{date_str}/{tenant_name}/{room_number}"
            else:
                record.name = 'New Collection'
    
    @api.depends('due_date', 'date')
    def _compute_days_late(self):
        for record in self:
            if record.due_date and record.date:
                delta = record.date - record.due_date
                record.days_late = max(0, delta.days)
            else:
                record.days_late = 0
    
    @api.onchange('room_id')
    def _onchange_room_id(self):
        if self.room_id:
            self.tenant_id = self.room_id.current_tenant_id
            self.agreement_id = self.room_id.current_agreement_id
            if self.agreement_id:
                self.amount_collected = self.agreement_id.rent_amount
                self.payment_method = self.agreement_id.payment_method
    
    @api.onchange('tenant_id')
    def _onchange_tenant_id(self):
        if self.tenant_id:
            # Set room and related fields
            self.room_id = self.tenant_id.current_room_id

            # Set agreement if available
            if self.tenant_id.current_agreement_id:
                self.agreement_id = self.tenant_id.current_agreement_id
                # Auto-populate amount based on agreement
                if self.collection_type == 'rent':
                    self.amount_collected = self.agreement_id.rent_amount
                elif self.collection_type == 'deposit':
                    self.amount_collected = self.agreement_id.deposit_amount
                elif self.collection_type == 'parking_charges':
                    self.amount_collected = self.agreement_id.parking_charges
                elif self.collection_type == 'parking_deposit':
                    self.amount_collected = self.agreement_id.parking_deposit

            # Set payment method from tenant preference
            if self.tenant_id.payment_method:
                self.payment_method = self.tenant_id.payment_method

            # Trigger period calculation if collection type is rent or parking
            if self.collection_type in ['rent', 'parking_charges'] and self.date:
                self._onchange_date_collection_type()

            # Return domain for room field to show only tenant's current room
            return {
                'domain': {
                    'room_id': [('current_tenant_id', '=', self.tenant_id.id)],
                    'agreement_id': [('tenant_id', '=', self.tenant_id.id)]
                }
            }
        else:
            # Clear related fields when tenant is cleared
            self.room_id = False
            self.agreement_id = False
            self.period_from = False
            self.period_to = False
            self.due_date = False
            return {
                'domain': {
                    'room_id': [],
                    'agreement_id': []
                }
            }
    
    @api.onchange('collection_type', 'agreement_id', 'other_charge_id')
    def _onchange_collection_type(self):
        if self.collection_type and self.agreement_id:
            if self.collection_type == 'rent':
                self.amount_collected = self.agreement_id.rent_amount
            elif self.collection_type == 'deposit':
                self.amount_collected = self.agreement_id.deposit_amount
            elif self.collection_type == 'parking_charges':
                self.amount_collected = self.agreement_id.parking_charges
            elif self.collection_type == 'parking_deposit':
                self.amount_collected = self.agreement_id.parking_deposit
            elif self.collection_type == 'extra':
                self.amount_collected = self.agreement_id.extra_charges
        
        # Handle other charges
        if self.collection_type == 'other_charges' and self.other_charge_id:
            # Look for agreement-specific charge amount or use default
            agreement_charge = self.env['property.agreement.charges'].search([
                ('agreement_id', '=', self.agreement_id.id),
                ('charge_id', '=', self.other_charge_id.id),
                ('active', '=', True)
            ], limit=1)
            
            if agreement_charge:
                self.amount_collected = agreement_charge.amount
            else:
                self.amount_collected = self.other_charge_id.amount
    
    @api.onchange('other_charge_id')
    def _onchange_other_charge_id(self):
        if self.other_charge_id and self.collection_type == 'other_charges':
            # Look for agreement-specific charge amount or use default
            if self.agreement_id:
                agreement_charge = self.env['property.agreement.charges'].search([
                    ('agreement_id', '=', self.agreement_id.id),
                    ('charge_id', '=', self.other_charge_id.id),
                    ('active', '=', True)
                ], limit=1)
                
                if agreement_charge:
                    self.amount_collected = agreement_charge.amount
                else:
                    self.amount_collected = self.other_charge_id.amount
            else:
                self.amount_collected = self.other_charge_id.amount
    
    @api.constrains('amount_collected')
    def _check_amount_positive(self):
        for record in self:
            if record.amount_collected <= 0:
                raise ValidationError(_('Collection amount must be positive!'))
    
    def action_collect(self):
        self.write({'status': 'collected'})
        # Generate receipt number
        if not self.receipt_number:
            sequence = self.env['ir.sequence'].next_by_code('property.collection') or '/'
            self.receipt_number = sequence
    
    def action_verify(self):
        self.write({
            'status': 'verified',
            'verified_by': self.env.user.id,
            'verification_date': fields.Datetime.now(),
        })
    
    def action_deposit(self):
        self.write({'status': 'deposited'})
    
    def action_cancel(self):
        self.write({'status': 'cancelled'})
    
    def action_print_receipt(self):
        # Simple receipt printing - can be enhanced with proper report
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'property.collection',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    @api.model
    def create_daily_collections_reminder(self):
        """Cron job to create daily collection reminders"""
        today = fields.Date.today()
        
        # Find all active agreements
        active_agreements = self.env['property.agreement'].search([('state', '=', 'active')])
        
        for agreement in active_agreements:
            # Check if collection is due based on payment frequency
            last_collection = self.search([
                ('agreement_id', '=', agreement.id),
                ('collection_type', '=', 'rent'),
                ('status', 'in', ['collected', 'verified', 'deposited'])
            ], order='date desc', limit=1)
            
            if agreement.payment_frequency == 'monthly':
                # Monthly payment due on specific day
                if today.day == agreement.payment_day:
                    self._create_due_reminder(agreement, today)
            elif agreement.payment_frequency == 'daily':
                # Daily payment
                if not last_collection or last_collection.date < today:
                    self._create_due_reminder(agreement, today)
    
    def _create_due_reminder(self, agreement, due_date):
        """Create a due reminder activity"""
        agreement.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=f'Rent Collection Due - {agreement.tenant_id.name}',
            note=f'Monthly rent of {agreement.rent_amount} is due for room {agreement.room_id.name}',
            date_deadline=due_date,
            user_id=agreement.room_id.property_id.manager_id.id,
        )
    
    # ========== INVOICE PAYMENT INTEGRATION ==========
    
    # Collection type to invoice type mapping
    COLLECTION_TO_INVOICE_TYPE = {
        'rent': 'rent',
        'deposit': 'deposit',
        'parking_charges': 'parking',
        'parking_deposit': 'parking',
        'maintenance': 'maintenance',
        'utility': 'utility',
        'penalty': 'penalty',
        'other_charges': 'other',
        'extra': 'other',
        'token': 'deposit',
        'other': 'other',
    }
    
    def _register_payment_for_collection(self):
        """Register payment against matching invoices when collection is recorded"""
        self.ensure_one()
        
        # Find matching unpaid invoices
        invoices = self._find_matching_invoices()
        
        if not invoices:
            # No invoices to pay - this is OK, invoice might be generated later
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(f"No matching invoices found for collection {self.name}")
            return
        
        # Create payment record
        payment = self._create_payment_from_collection(invoices)
        
        if payment:
            # Link payment to collection
            self.write({
                'payment_id': payment.id,
                'matched_invoice_ids': [(6, 0, invoices.ids)],
                'payment_reference': payment.name,
            })
            
            # Post the payment to reconcile with invoices
            if payment.state == 'draft':
                payment.action_post()
            
            # Reconcile payment with invoices
            self._reconcile_payment_with_invoices(payment, invoices)
    
    def _find_matching_invoices(self):
        """Find unpaid invoices that match this collection"""
        self.ensure_one()
        
        import logging
        _logger = logging.getLogger(__name__)
        
        # Map collection type to invoice type
        invoice_type = self.COLLECTION_TO_INVOICE_TYPE.get(self.collection_type)
        
        if not invoice_type:
            _logger.info(f"Collection {self.name}: No invoice type mapping for collection_type='{self.collection_type}'")
            return self.env['account.move']
        
        # Build search domain - start with basic criteria
        domain = [
            ('tenant_id', '=', self.tenant_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ]
        
        _logger.info(f"Collection {self.name}: Searching for invoices with tenant={self.tenant_id.name}, type=out_invoice, state=posted")
        
        # Try with invoice_type first
        domain_with_type = domain + [('invoice_type', '=', invoice_type)]
        
        # Add agreement filter if available
        if self.agreement_id:
            domain_with_type.append(('agreement_id', '=', self.agreement_id.id))
            _logger.info(f"  - With agreement={self.agreement_id.name}")
        
        # Add period filter for rent/parking (optional - try with and without)
        if self.collection_type in ['rent', 'parking_charges'] and self.period_from and self.period_to:
            domain_with_period = domain_with_type + [
                ('period_from', '<=', self.period_to),
                ('period_to', '>=', self.period_from),
            ]
            _logger.info(f"  - With period overlap: {self.period_from} to {self.period_to}")
            invoices = self.env['account.move'].search(domain_with_period, order='invoice_date asc', limit=10)
            
            if invoices:
                _logger.info(f"  ✓ Found {len(invoices)} invoice(s) with period matching")
                return invoices
            else:
                _logger.info(f"  - No invoices found with period matching, trying without period filter...")
        
        # Try without period filter
        invoices = self.env['account.move'].search(domain_with_type, order='invoice_date asc', limit=10)
        
        if invoices:
            _logger.info(f"  ✓ Found {len(invoices)} invoice(s) with invoice_type={invoice_type}")
            return invoices
        
        # Try without invoice_type (more lenient)
        _logger.info(f"  - No invoices found with invoice_type={invoice_type}, trying without invoice_type...")
        invoices = self.env['account.move'].search(domain, order='invoice_date asc', limit=10)
        
        if invoices:
            _logger.info(f"  ✓ Found {len(invoices)} invoice(s) without invoice_type filter")
            return invoices
        
        _logger.info(f"  ✗ No matching invoices found for collection {self.name}")
        return self.env['account.move']
    
    def _create_payment_from_collection(self, invoices):
        """Create account.payment record from collection"""
        self.ensure_one()
        
        if not invoices or not self.tenant_id or not self.tenant_id.partner_id:
            return False
        
        # Determine payment journal based on payment method
        journal = self._get_payment_journal()
        
        if not journal:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"No suitable journal found for payment method {self.payment_method}")
            return False
        
        # Create payment
        payment_vals = {
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.tenant_id.partner_id.id,
            'amount': self.amount_collected,
            'date': self.date,
            'journal_id': journal.id,
            'collection_id': self.id,
        }
        
        # Add tenant_id if the field exists (from our custom extension)
        payment_vals['tenant_id'] = self.tenant_id.id
        
        # Create payment
        payment = self.env['account.payment'].create(payment_vals)
        
        # Link payment to invoices via reconciliation
        # This happens automatically when payment is posted via action_post()
        # Odoo matches partner_id and reconciles outstanding receivables
        
        return payment
    
    def _reconcile_payment_with_invoices(self, payment, invoices):
        """Reconcile payment with invoices by matching receivable account lines"""
        self.ensure_one()
        
        if not payment or not invoices:
            return
        
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get receivable account from partner
        receivable_account = self.tenant_id.partner_id.property_account_receivable_id
        
        if not receivable_account:
            _logger.warning(f"No receivable account found for partner {self.tenant_id.partner_id.name}")
            return
        
        # Get payment move lines (credit lines on receivable account)
        payment_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == receivable_account and line.credit > 0 and not line.reconciled
        )
        
        # Get invoice move lines (debit lines on receivable account)
        invoice_lines = invoices.mapped('line_ids').filtered(
            lambda line: line.account_id == receivable_account and line.debit > 0 and not line.reconciled
        )
        
        if not payment_lines or not invoice_lines:
            _logger.warning(f"Could not find unreconciled lines for payment {payment.name} and invoices {invoices.mapped('name')}")
            return
        
        # Reconcile the lines
        lines_to_reconcile = payment_lines + invoice_lines
        
        try:
            lines_to_reconcile.reconcile()
            _logger.info(f"✓ Reconciled payment {payment.name} with invoices {invoices.mapped('name')}")
        except Exception as e:
            _logger.error(f"Failed to reconcile payment {payment.name}: {str(e)}")
    
    def _get_payment_journal(self):
        """Get appropriate journal based on payment method"""
        self.ensure_one()
        
        # Map payment method to journal type
        if self.payment_method in ['cash']:
            journal_type = 'cash'
        elif self.payment_method in ['bank_transfer', 'cheque', 'online', 'card']:
            journal_type = 'bank'
        else:
            journal_type = 'cash'  # default
        
        # Find suitable journal
        journal = self.env['account.journal'].search([
            ('type', '=', journal_type),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        
        return journal
    
    # ========== END INVOICE PAYMENT INTEGRATION ==========
