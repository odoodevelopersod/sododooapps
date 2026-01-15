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
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class PropertyOutstandingDues(models.Model):
    _name = 'property.outstanding.dues'
    _description = 'Outstanding Dues Summary'
    _order = 'total_outstanding desc, tenant_id'
    _rec_name = 'tenant_id'

    # Relations
    tenant_id = fields.Many2one('property.tenant', 'Tenant', required=True)
    room_id = fields.Many2one('property.room', 'Room', required=True)
    agreement_id = fields.Many2one('property.agreement', 'Agreement')
    
    # Outstanding Amounts
    rent_outstanding = fields.Monetary('Rent Outstanding', currency_field='currency_id')
    deposit_outstanding = fields.Monetary('Deposit Outstanding', currency_field='currency_id')
    parking_outstanding = fields.Monetary('Parking Outstanding', currency_field='currency_id')
    other_charges_outstanding = fields.Monetary('Other Charges Outstanding', currency_field='currency_id')
    total_outstanding = fields.Monetary('Total Outstanding', currency_field='currency_id', 
                                       compute='_compute_total_outstanding', store=True)
    
    # Period Information
    last_payment_date = fields.Date('Last Payment Date')
    months_overdue = fields.Integer('Months Overdue', compute='_compute_overdue_months')
    days_overdue = fields.Integer('Days Overdue', compute='_compute_overdue_days')
    
    # Status
    status = fields.Selection([
        ('current', 'Current'),
        ('overdue_30', 'Overdue (1-30 days)'),
        ('overdue_60', 'Overdue (31-60 days)'),
        ('overdue_90', 'Overdue (61-90 days)'),
        ('overdue_90plus', 'Overdue (90+ days)'),
        ('critical', 'Critical (180+ days)'),
    ], string='Status', compute='_compute_status', store=True)
    
    # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Computed Fields for Details
    next_due_date = fields.Date('Next Due Date', compute='_compute_next_due_date')
    expected_monthly_amount = fields.Monetary('Expected Monthly Amount', currency_field='currency_id',
                                            compute='_compute_expected_amount')
    
    @api.depends('rent_outstanding', 'deposit_outstanding', 'parking_outstanding', 'other_charges_outstanding')
    def _compute_total_outstanding(self):
        for record in self:
            record.total_outstanding = (record.rent_outstanding + record.deposit_outstanding + 
                                      record.parking_outstanding + record.other_charges_outstanding)
    
    @api.depends('last_payment_date')
    def _compute_overdue_months(self):
        today = fields.Date.today()
        for record in self:
            if record.last_payment_date:
                delta = relativedelta(today, record.last_payment_date)
                record.months_overdue = delta.months + (delta.years * 12)
            else:
                record.months_overdue = 0
    
    @api.depends('last_payment_date')
    def _compute_overdue_days(self):
        today = fields.Date.today()
        for record in self:
            if record.last_payment_date:
                delta = today - record.last_payment_date
                record.days_overdue = delta.days
            else:
                record.days_overdue = 0
    
    @api.depends('days_overdue', 'total_outstanding')
    def _compute_status(self):
        for record in self:
            if record.total_outstanding <= 0:
                record.status = 'current'
            elif record.days_overdue <= 30:
                record.status = 'overdue_30'
            elif record.days_overdue <= 60:
                record.status = 'overdue_60'
            elif record.days_overdue <= 90:
                record.status = 'overdue_90'
            elif record.days_overdue <= 180:
                record.status = 'overdue_90plus'
            else:
                record.status = 'critical'
    
    @api.depends('agreement_id', 'agreement_id.payment_day')
    def _compute_next_due_date(self):
        today = fields.Date.today()
        for record in self:
            if record.agreement_id and record.agreement_id.payment_day:
                # Calculate next due date based on payment day
                next_month = today.replace(day=1) + relativedelta(months=1)
                try:
                    record.next_due_date = next_month.replace(day=record.agreement_id.payment_day)
                except ValueError:
                    # Handle cases like February 30th
                    record.next_due_date = next_month.replace(day=28)
            else:
                record.next_due_date = False
    
    @api.depends('agreement_id')
    def _compute_expected_amount(self):
        for record in self:
            if record.agreement_id:
                record.expected_monthly_amount = (record.agreement_id.rent_amount + 
                                                record.agreement_id.parking_charges)
            else:
                record.expected_monthly_amount = 0
    
    @api.model
    def update_outstanding_dues(self):
        """Method to calculate and update outstanding dues for all active tenants"""
        
        # Clear existing records
        self.search([]).unlink()
        
        # Get all active tenants with current agreements
        tenants = self.env['property.tenant'].search([
            ('status', '=', 'active'),
            ('current_room_id', '!=', False),
            ('current_agreement_id', '!=', False)
        ])
        
        for tenant in tenants:
            agreement = tenant.current_agreement_id
            if not agreement or agreement.state != 'active':
                continue
            
            # Calculate outstanding amounts
            rent_outstanding = self._calculate_rent_outstanding(tenant, agreement)
            deposit_outstanding = self._calculate_deposit_outstanding(tenant, agreement)
            parking_outstanding = self._calculate_parking_outstanding(tenant, agreement)
            other_charges_outstanding = self._calculate_other_charges_outstanding(tenant, agreement)
            
            # Get last payment date
            last_collection = self.env['property.collection'].search([
                ('tenant_id', '=', tenant.id),
                ('active', '=', True)
            ], limit=1, order='date desc')
            
            last_payment_date = last_collection.date if last_collection else agreement.start_date
            
            # Create outstanding dues record only if there are outstanding amounts
            if any([rent_outstanding, deposit_outstanding, parking_outstanding, other_charges_outstanding]):
                self.create({
                    'tenant_id': tenant.id,
                    'room_id': tenant.current_room_id.id,
                    'agreement_id': agreement.id,
                    'rent_outstanding': rent_outstanding,
                    'deposit_outstanding': deposit_outstanding,
                    'parking_outstanding': parking_outstanding,
                    'other_charges_outstanding': other_charges_outstanding,
                    'last_payment_date': last_payment_date,
                })
    
    def _calculate_rent_outstanding(self, tenant, agreement):
        """Calculate outstanding rent amount from unpaid invoices"""
        # Query unpaid rent invoices for this tenant/agreement
        unpaid_invoices = self.env['account.move'].search([
            ('tenant_id', '=', tenant.id),
            ('agreement_id', '=', agreement.id),
            ('move_type', '=', 'out_invoice'),
            ('invoice_type', '=', 'rent'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ])
        
        # Sum the unpaid amounts (amount_residual)
        total_outstanding = sum(unpaid_invoices.mapped('amount_residual'))
        
        return max(0, total_outstanding)
    
    def _calculate_deposit_outstanding(self, tenant, agreement):
        """Calculate outstanding deposit amount from unpaid invoices"""
        # Query unpaid deposit invoices for this tenant/agreement
        unpaid_invoices = self.env['account.move'].search([
            ('tenant_id', '=', tenant.id),
            ('agreement_id', '=', agreement.id),
            ('move_type', '=', 'out_invoice'),
            ('invoice_type', '=', 'deposit'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ])
        
        # Sum the unpaid amounts
        total_outstanding = sum(unpaid_invoices.mapped('amount_residual'))
        
        return max(0, total_outstanding)
    
    def _calculate_parking_outstanding(self, tenant, agreement):
        """Calculate outstanding parking charges from unpaid invoices"""
        # Query unpaid parking invoices for this tenant/agreement
        unpaid_invoices = self.env['account.move'].search([
            ('tenant_id', '=', tenant.id),
            ('agreement_id', '=', agreement.id),
            ('move_type', '=', 'out_invoice'),
            ('invoice_type', 'in', ['parking', 'parking_charges']),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ])
        
        # Sum the unpaid amounts
        total_outstanding = sum(unpaid_invoices.mapped('amount_residual'))
        
        return max(0, total_outstanding)
    
    def _calculate_other_charges_outstanding(self, tenant, agreement):
        """Calculate outstanding other charges from unpaid invoices"""
        # Query unpaid other charges invoices for this tenant/agreement
        unpaid_invoices = self.env['account.move'].search([
            ('tenant_id', '=', tenant.id),
            ('agreement_id', '=', agreement.id),
            ('move_type', '=', 'out_invoice'),
            ('invoice_type', 'in', ['maintenance', 'utility', 'penalty', 'other']),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ])
        
        # Sum the unpaid amounts
        total_outstanding = sum(unpaid_invoices.mapped('amount_residual'))
        
        return max(0, total_outstanding)
    
    def action_view_tenant_collections(self):
        """View all collections for this tenant"""
        return {
            'name': _('Tenant Collections'),
            'view_mode': 'list,form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'domain': [('tenant_id', '=', self.tenant_id.id), ('active', '=', True)],
            'context': {'default_tenant_id': self.tenant_id.id}
        }
    
    def action_create_collection(self):
        """Create a new collection for this tenant"""
        return {
            'name': _('Create Collection'),
            'view_mode': 'form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_tenant_id': self.tenant_id.id,
                'default_room_id': self.room_id.id,
                'default_agreement_id': self.agreement_id.id,
                'default_amount_collected': self.expected_monthly_amount,
            }
        }

    @api.model
    def cron_update_outstanding_dues(self):
        """Cron job to update outstanding dues daily"""
        self.update_outstanding_dues()