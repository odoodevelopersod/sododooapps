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
from odoo import models, fields, api
from datetime import datetime, timedelta


class PropertyStatement(models.Model):
    _name = 'property.statement'
    _description = 'Customer Statement of Account'
    _order = 'transaction_date asc, id asc'  # Changed to ascending for natural reading
    _rec_name = 'reference'

    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True, ondelete='cascade')
    transaction_date = fields.Date(string='Transaction Date', required=True, default=fields.Date.context_today)
    reference = fields.Char(string='Reference', required=True)
    description = fields.Text(string='Description')
    transaction_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('deposit', 'Security Deposit'),
        ('rent', 'Rent Payment'),
        ('parking', 'Parking'),
        ('outstanding', 'Outstanding Balance'),
        ('other', 'Other'),
    ], string='Transaction Type', required=True)
    debit_amount = fields.Monetary('Debit', currency_field='currency_id', default=0.0)
    credit_amount = fields.Monetary('Credit', currency_field='currency_id', default=0.0)
    running_balance = fields.Float(string='Running Balance', digits=(16, 2), compute='_compute_running_balance', store=True)
    
    room_id = fields.Many2one('property.room', string='Room')
    agreement_id = fields.Many2one('property.agreement', string='Agreement', ondelete='cascade')
    collection_id = fields.Many2one('property.collection', string='Collection')
    
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    @api.depends('tenant_id', 'transaction_date', 'debit_amount', 'credit_amount')
    def _compute_running_balance(self):
        # Process each statement individually to ensure correct chronological balance
        for record in self:
            if not record.tenant_id:
                record.running_balance = 0.0
                continue
            
            # Search ALL statements for this tenant up to and including this one
            # Order by date first, then by ID for same-date transactions
            previous_statements = self.search([
                ('tenant_id', '=', record.tenant_id.id),
                '|',
                ('transaction_date', '<', record.transaction_date),
                '&',
                ('transaction_date', '=', record.transaction_date),
                ('id', '<=', record.id)
            ], order='transaction_date asc, id asc')
            
            # Calculate cumulative balance
            balance = 0.0
            for stmt in previous_statements:
                balance += stmt.debit_amount - stmt.credit_amount
            
            record.running_balance = balance

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.reference} - {record.tenant_id.name}"
            result.append((record.id, name))
        return result

    @api.model
    def create_from_collection(self, collection):
        """Create statement entry from collection record"""
        description = f"Payment for {collection.collection_type}"
        if collection.room_id:
            description += f" - Room {collection.room_id.name}"
        
        transaction_type = 'rent'
        if collection.collection_type == 'deposit':
            transaction_type = 'deposit'
        elif collection.collection_type == 'parking':
            transaction_type = 'parking'
        elif collection.collection_type == 'other':
            transaction_type = 'other_charges'
        
        vals = {
            'tenant_id': collection.tenant_id.id,
            'transaction_date': collection.date,
            'reference': collection.receipt_number or f"COL/{collection.id}",
            'description': description,
            'transaction_type': transaction_type,
            'credit_amount': collection.amount_collected,
            'debit_amount': 0.0,
            'room_id': collection.room_id.id if collection.room_id else False,
            'agreement_id': collection.agreement_id.id if collection.agreement_id else False,
            'collection_id': collection.id,
        }
        
        return self.create(vals)

    @api.model
    def create_from_agreement(self, agreement):
        """Create statement entries from agreement charges"""
        statements = self.env['property.statement']
        
        # Security deposit entry
        if agreement.deposit_amount > 0:
            vals = {
                'tenant_id': agreement.tenant_id.id,
                'transaction_date': agreement.start_date,
                'reference': f"AGR/{agreement.id}/DEPOSIT",
                'description': f"Security deposit for agreement {agreement.name}",
                'transaction_type': 'deposit',
                'debit_amount': agreement.deposit_amount,
                'credit_amount': 0.0,
                'room_id': agreement.room_id.id,
                'agreement_id': agreement.id,
            }
            statements += self.create(vals)
        
        # Monthly rent entries - only create up to today (never future months)
        today = fields.Date.today()
        
        # Use the earlier of: agreement end_date or today
        # This ensures we never create future charges
        end_limit = min(agreement.end_date, today)
        
        current_date = agreement.start_date
        while current_date <= end_limit:
            vals = {
                'tenant_id': agreement.tenant_id.id,
                'transaction_date': current_date,
                'reference': f"AGR/{agreement.id}/RENT/{current_date.strftime('%Y%m')}",
                'description': f"Monthly rent for {current_date.strftime('%B %Y')}",
                'transaction_type': 'rent',
                'debit_amount': agreement.rent_amount,
                'credit_amount': 0.0,
                'room_id': agreement.room_id.id,
                'agreement_id': agreement.id,
            }
            statements += self.create(vals)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return statements


class PropertyTenant(models.Model):
    _inherit = 'property.tenant'

    statement_ids = fields.One2many('property.statement', 'tenant_id', string='Statement of Account')
    statement_count = fields.Integer(string='Statement Entries', compute='_compute_statement_count')
    total_debits = fields.Float(string='Total Debits', compute='_compute_statement_totals')
    total_credits = fields.Float(string='Total Credits', compute='_compute_statement_totals')
    current_balance = fields.Float(string='Current Balance', compute='_compute_statement_totals')

    @api.depends('statement_ids')
    def _compute_statement_count(self):
        for tenant in self:
            tenant.statement_count = len(tenant.statement_ids)

    @api.depends('statement_ids.debit_amount', 'statement_ids.credit_amount', 'statement_ids.agreement_id.state')
    def _compute_statement_totals(self):
        for tenant in self:
            # Only count statement entries from ACTIVE agreements
            # Exclude terminated agreements to match outstanding dues logic
            active_statements = tenant.statement_ids.filtered(
                lambda s: not s.agreement_id or s.agreement_id.state == 'active'
            )
            
            tenant.total_debits = sum(active_statements.mapped('debit_amount'))
            tenant.total_credits = sum(active_statements.mapped('credit_amount'))
            tenant.current_balance = tenant.total_debits - tenant.total_credits

    def action_view_statement(self):
        """Action to view tenant's statement of account"""
        self.ensure_one()
        return {
            'name': f'Statement of Account - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'property.statement',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {
                'default_tenant_id': self.id,
                'search_default_tenant_id': self.id,
            },
            'target': 'current',
        }

    def action_generate_statement_report(self):
        """Generate statement report for specific period"""
        return {
            'name': 'Generate Statement Report',
            'type': 'ir.actions.act_window',
            'res_model': 'property.statement.wizard',
            'view_mode': 'form',
            'context': {
                'default_tenant_id': self.id,
            },
            'target': 'new',
        }


class PropertyCollection(models.Model):
    _inherit = 'property.collection'

    statement_id = fields.Many2one('property.statement', string='Statement Entry', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        collections = super().create(vals_list)
        for collection in collections:
            if collection.tenant_id and collection.status in ['collected', 'verified', 'deposited']:
                statement = self.env['property.statement'].create_from_collection(collection)
                collection.statement_id = statement.id
        return collections

    def write(self, vals):
        result = super().write(vals)
        for collection in self:
            if 'status' in vals and vals['status'] in ['collected', 'verified', 'deposited'] and collection.tenant_id and not collection.statement_id:
                try:
                    # Use savepoint to isolate constraint violations
                    with self.env.cr.savepoint():
                        statement = self.env['property.statement'].create_from_collection(collection)
                        collection.statement_id = statement.id
                except Exception as e:
                    # Skip duplicates silently (SQL constraint violation)
                    if 'unique_agreement_transaction' not in str(e) and 'duplicate' not in str(e).lower():
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.error(f"Failed to create statement for collection {collection.id}: {str(e)}")
        return result
    
    @api.model
    def cron_create_missing_collection_statements(self):
        """Batch create statement entries for collections without them"""
        # Find all collected/verified/deposited collections without statement entries
        collections = self.search([
            ('status', 'in', ['collected', 'verified', 'deposited']),
            ('statement_id', '=', False),
            ('tenant_id', '!=', False)
        ])
        
        created_count = 0
        skipped_count = 0
        for collection in collections:
            # Use savepoint to isolate constraint violations
            try:
                with self.env.cr.savepoint():
                    statement = self.env['property.statement'].create_from_collection(collection)
                    collection.statement_id = statement.id
                    created_count += 1
            except Exception as e:
                # Skip duplicates silently (SQL constraint violation)
                error_msg = str(e)
                if 'unique_agreement_transaction' in error_msg or 'duplicate' in error_msg.lower():
                    skipped_count += 1
                else:
                    # Log other errors
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.error(f"Failed to create statement for collection {collection.id}: {error_msg}")
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Created statement entries for {created_count} collections (skipped {skipped_count} duplicates)")
        
        return True
    
    @api.model
    def cron_recalculate_running_balances(self):
        """Recalculate running balances for all statement entries"""
        import logging
        _logger = logging.getLogger(__name__)
        
        # Get all statement entries
        all_statements = self.search([], order='transaction_date asc, id asc')
        
        if not all_statements:
            _logger.info("No statement entries found to recalculate")
            return True
        
        _logger.info(f"Recalculating running balances for {len(all_statements)} statements...")
        
        # Trigger recomputation for all statements
        # This will use the _compute_running_balance method
        all_statements._compute_running_balance()
        
        _logger.info(f"Running balances recalculated successfully")
        
        return True


class PropertyAgreement(models.Model):
    _inherit = 'property.agreement'

    statement_ids = fields.One2many('property.statement', 'agreement_id', string='Statement Entries')

    def action_generate_statement_entries(self):
        """Generate statement entries for this agreement"""
        self.ensure_one()
        if not self.statement_ids:
            statements = self.env['property.statement'].create_from_agreement(self)
            return {
                'name': 'Statement Entries Generated',
                'type': 'ir.actions.act_window',
                'res_model': 'property.statement',
                'view_mode': 'list',
                'domain': [('id', 'in', statements.ids)],
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Statement entries already exist for this agreement.',
                    'type': 'warning',
                }
            }
    
    def write(self, vals):
        """Auto-generate statement entries when agreement becomes active"""
        result = super().write(vals)
        
        # If state changes to active and no statement entries exist, generate them
        if 'state' in vals and vals['state'] == 'active':
            for agreement in self:
                if not agreement.statement_ids:
                    self.env['property.statement'].create_from_agreement(agreement)
        
        return result
    
    @api.model
    def cron_generate_missing_statement_entries(self):
        """Batch generate statement entries for all agreements without them"""
        # Find all ACTIVE agreements without statement entries
        # Changed from 'active, terminated' to just 'active'
        agreements = self.search([
            ('state', '=', 'active'),
            ('statement_ids', '=', False)
        ])
        
        generated_count = 0
        for agreement in agreements:
            try:
                self.env['property.statement'].create_from_agreement(agreement)
                generated_count += 1
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to generate statement for agreement {agreement.id}: {str(e)}")
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Generated statement entries for {generated_count} out of {len(agreements)} agreements")
        
        return True
    
    @api.model
    def cron_cleanup_and_regenerate_statement_entries(self):
        """Clean up and regenerate all statement entries for agreements"""
        
        # Delete ALL rent and deposit statement entries
        # This includes both active ones AND orphaned ones (where agreement was deleted)
        all_statements = self.env['property.statement'].search([
            ('transaction_type', 'in', ['rent', 'deposit'])
            # Removed agreement_id filter to catch orphaned entries too
        ])
        
        deleted_count = len(all_statements)
        all_statements.unlink()
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Deleted {deleted_count} existing statement entries (including orphaned ones)")
        
        # Find ONLY ACTIVE agreements (not terminated ones)
        # This prevents duplicates from old terminated agreements
        agreements = self.search([('state', '=', 'active')])
        
        regenerated_count = 0
        for agreement in agreements:
            try:
                self.env['property.statement'].create_from_agreement(agreement)
                regenerated_count += 1
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error(f"Failed to regenerate statement for agreement {agreement.id}: {str(e)}")
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f"Regenerated statement entries for {regenerated_count} active agreements")
        
        return True