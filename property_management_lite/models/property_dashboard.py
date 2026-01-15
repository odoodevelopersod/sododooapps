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
from odoo import api, fields, models
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class PropertyDashboard(models.TransientModel):
    _name = 'property.dashboard'
    _description = 'Property Management Dashboard'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Name', default='Property Management Dashboard', readonly=True)

    def name_get(self):
        """Return proper display name"""
        result = []
        for record in self:
            result.append((record.id, 'Property Management Dashboard'))
        return result

    @api.model
    def default_get(self, fields_list):
        """Override to ensure fresh data is always computed"""
        res = super().default_get(fields_list)
        
        # Compute fresh values directly in the result
        today = fields.Date.today()
        
        # Today's collections
        collections = self.env['property.collection'].search([
            ('date', '=', today),
            ('status', '!=', 'cancelled')
        ])
        res['today_collections'] = sum(collections.mapped('amount_collected'))
        res['today_collections_count'] = len(collections)
        
        # Today's expenses
        expenses = self.env['account.move'].search([
            ('move_type','in', ('in_invoice','in_refund')),
            ('invoice_date', '=', today),
            ('state', 'in', ['posted'])
        ])
        res['today_expenses'] = sum(expenses.mapped('amount_total'))
        res['today_expenses_count'] = len(expenses)
        res['today_profit'] = res['today_collections'] - res['today_expenses']
        
        # Today's new tenants
        tenants = self.env['property.tenant'].search([
            ('create_date', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
            ('create_date', '<', fields.Datetime.to_string(datetime.combine(today + timedelta(days=1), datetime.min.time())))
        ])
        res['today_new_tenants'] = len(tenants)
        
        # Vacant rooms today
        vacant_rooms = self.env['property.room'].search([('status', '=', 'vacant')])
        res['today_vacant_rooms'] = len(vacant_rooms)
        
        # Week stats
        week_start = today - timedelta(days=today.weekday())
        week_collections = self.env['property.collection'].search([
            ('date', '>=', week_start),
            ('date', '<=', today),
            ('status', '!=', 'cancelled')
        ])
        res['week_collections'] = sum(week_collections.mapped('amount_collected'))
        res['week_collections_count'] = len(week_collections)
        
        # Week expenses
        week_expenses = self.env['account.move'].search([
            ('move_type','in', ('in_invoice','in_refund')),
            ('invoice_date', '>=', week_start),
            ('invoice_date', '<=', today),
            ('state', 'in', ['posted'])
        ])
        res['week_expenses'] = sum(week_expenses.mapped('amount_total'))
        res['week_expenses_count'] = len(week_expenses)
        res['week_profit'] = res['week_collections'] - res['week_expenses']
        
        week_start_datetime = fields.Datetime.to_string(datetime.combine(week_start, datetime.min.time()))
        today_end_datetime = fields.Datetime.to_string(datetime.combine(today + timedelta(days=1), datetime.min.time()))
        week_tenants = self.env['property.tenant'].search([
            ('create_date', '>=', week_start_datetime),
            ('create_date', '<', today_end_datetime)
        ])
        res['week_new_tenants'] = len(week_tenants)
        
        # Month stats
        month_start = today.replace(day=1)
        month_collections = self.env['property.collection'].search([
            ('date', '>=', month_start),
            ('date', '<=', today),
            ('status', '!=', 'cancelled')
        ])
        res['month_collections'] = sum(month_collections.mapped('amount_collected'))
        res['month_collections_count'] = len(month_collections)
        
        # Month expenses
        month_expenses = self.env['account.move'].search([
            ('move_type','in', ('in_invoice','in_refund')),
            ('invoice_date', '>=', month_start),
            ('invoice_date', '<=', today),
            ('state', 'in', ['posted'])
        ])
        res['month_expenses'] = sum(month_expenses.mapped('amount_total'))
        res['month_expenses_count'] = len(month_expenses)
        res['month_profit'] = res['month_collections'] - res['month_expenses']
        
        month_start_datetime = fields.Datetime.to_string(datetime.combine(month_start, datetime.min.time()))
        today_end_datetime = fields.Datetime.to_string(datetime.combine(today + timedelta(days=1), datetime.min.time()))
        month_tenants = self.env['property.tenant'].search([
            ('create_date', '>=', month_start_datetime),
            ('create_date', '<', today_end_datetime)
        ])
        res['month_new_tenants'] = len(month_tenants)
        
        # Overall stats
        res['total_properties'] = self.env['property.property'].search_count([])
        
        all_rooms = self.env['property.room'].search([])
        res['total_rooms'] = len(all_rooms)
        
        occupied_rooms = all_rooms.filtered(lambda r: r.status == 'occupied')
        res['occupied_rooms'] = len(occupied_rooms)
        res['vacant_rooms'] = res['total_rooms'] - res['occupied_rooms']
        
        # Calculate occupancy rate as a decimal (0.0 to 1.0)
        # The percentage widget in the view will multiply by 100 for display
        if res['total_rooms'] > 0:
            res['occupancy_rate'] = res['occupied_rooms'] / res['total_rooms']
        else:
            res['occupancy_rate'] = 0.0
        
        res['total_tenants'] = self.env['property.tenant'].search_count([('status', '=', 'active')])
        
        # Agent Statistics
        all_agents = self.env['res.partner'].search([
            ('is_company', '=', False),
            '|', ('category_id.name', 'in', ['Property Agent', 'Rental Agent', 'Sales Agent']),
            ('function', 'ilike', 'agent')
        ])
        res['total_agents'] = len(all_agents)
        
        # Count agents with active agreements
        active_agreements = self.env['property.agreement'].search([('state', '=', 'active')])
        agents_with_agreements = active_agreements.mapped('agent_id').filtered(lambda a: a)
        res['active_agents'] = len(set(agents_with_agreements.ids))
        res['agents_with_tenants'] = len(set(agents_with_agreements.ids))
        
        # Top performing agents by tenant count
        agent_performance = {}
        for agreement in active_agreements:
            if agreement.agent_id:
                agent_name = agreement.agent_id.name
                if agent_name not in agent_performance:
                    agent_performance[agent_name] = {
                        'tenant_count': 0,
                        'total_rent': 0,
                        'agent_id': agreement.agent_id.id
                    }
                agent_performance[agent_name]['tenant_count'] += 1
                agent_performance[agent_name]['total_rent'] += agreement.rent_amount
        
        # Sort agents by tenant count (descending)
        sorted_agents = sorted(agent_performance.items(), 
                             key=lambda x: x[1]['tenant_count'], 
                             reverse=True)
        
        # Format top agents list
        top_agents_text = ""
        for i, (agent_name, stats) in enumerate(sorted_agents[:10], 1):
            top_agents_text += f"{i}. {agent_name} - {stats['tenant_count']} tenants (AED {stats['total_rent']:,.0f}/month)\n"
        res['top_agents_list'] = top_agents_text or "No agents assigned to agreements"
        
        # Agent performance summary
        if agent_performance:
            avg_tenants = sum(stats['tenant_count'] for stats in agent_performance.values()) / len(agent_performance)
            avg_rent = sum(stats['total_rent'] for stats in agent_performance.values()) / len(agent_performance)
            max_tenants = max(stats['tenant_count'] for stats in agent_performance.values())
            min_tenants = min(stats['tenant_count'] for stats in agent_performance.values())
            
            performance_summary = f"Average tenants per agent: {avg_tenants:.1f}\n"
            performance_summary += f"Average monthly rent per agent: AED {avg_rent:,.0f}\n"
            performance_summary += f"Highest tenant count: {max_tenants}\n"
            performance_summary += f"Lowest tenant count: {min_tenants}\n"
            performance_summary += f"Agents without assignments: {res['total_agents'] - res['agents_with_tenants']}"
        else:
            performance_summary = "No agent performance data available"
        
        res['agent_performance_summary'] = performance_summary
        
        # Statement and Outstanding Dues Statistics
        # Total outstanding dues across all tenants
        outstanding_dues = self.env['property.outstanding.dues'].search([])
        res['total_outstanding_amount'] = sum(outstanding_dues.mapped('total_outstanding'))
        res['total_outstanding_count'] = len(outstanding_dues.filtered(lambda d: d.total_outstanding > 0))
        
        # Outstanding dues by status
        overdue_dues = outstanding_dues.filtered(lambda d: d.status in ['overdue_30', 'overdue_60', 'overdue_90', 'overdue_90plus', 'critical'])
        res['overdue_tenants_count'] = len(overdue_dues)
        res['overdue_amount'] = sum(overdue_dues.mapped('total_outstanding'))
        
        # Critical overdue (90+ days)
        critical_dues = outstanding_dues.filtered(lambda d: d.status in ['overdue_90', 'overdue_90plus', 'critical'])
        res['critical_overdue_count'] = len(critical_dues)
        res['critical_overdue_amount'] = sum(critical_dues.mapped('total_outstanding'))
        
        # Statement entries this month
        month_statements = self.env['property.statement'].search([
            ('transaction_date', '>=', month_start),
            ('transaction_date', '<=', today)
        ])
        res['month_statement_entries'] = len(month_statements)
        res['month_total_debits'] = sum(month_statements.mapped('debit_amount'))
        res['month_total_credits'] = sum(month_statements.mapped('credit_amount'))
        res['month_net_balance'] = res['month_total_debits'] - res['month_total_credits']
        
        
        # Tenant payment behavior analysis based on statement balances
        active_tenants = self.env['property.tenant'].search([('status', '=', 'active')])
        
        # Count tenants with credit balance (negative running balance = advance payment)
        # and debit balance (positive running balance = pending payment)
        tenants_credit = 0
        tenants_debit = 0
        
        for tenant in active_tenants:
            # Get latest statement entry for this tenant to get current running balance
            latest_statement = self.env['property.statement'].search([
                ('tenant_id', '=', tenant.id)
            ], order='transaction_date desc, id desc', limit=1)
            
            if latest_statement:
                if latest_statement.running_balance < 0:
                    tenants_credit += 1  # Negative balance = credit (advance payment)
                elif latest_statement.running_balance > 0:
                    tenants_debit += 1   # Positive balance = debit (pending payment)
        
        res['tenants_with_negative_balance'] = tenants_credit
        res['tenants_with_positive_balance'] = tenants_debit
        
        # Top debtors list
        top_debtors = outstanding_dues.filtered(lambda d: d.total_outstanding > 0).sorted('total_outstanding', reverse=True)[:10]
        debtors_text = ""
        for i, debtor in enumerate(top_debtors, 1):
            debtors_text += f"{i}. {debtor.tenant_id.name} - AED {debtor.total_outstanding:,.0f} ({debtor.status.replace('_', ' ').title()})\n"
        res['top_debtors_list'] = debtors_text or "No outstanding dues found"
        
        # Collection efficiency (payments vs expected)
        total_expected = res['month_total_debits']
        total_collected = res['month_total_credits']
        if total_expected > 0:
            res['collection_efficiency'] = (total_collected / total_expected)
        else:
            res['collection_efficiency'] = 0.0
        
        # Recent activities
        recent_collections = self.env['property.collection'].search([
            ('status', '!=', 'cancelled')
        ], order='date desc', limit=5)
        
        collections_text = ""
        for collection in recent_collections:
            collections_text += f"• {collection.date} - {collection.tenant_id.name} - {collection.amount_collected} AED\n"
        res['recent_collections'] = collections_text or "No recent collections"
        
        recent_tenants = self.env['property.tenant'].search([], order='create_date desc', limit=5)
        tenants_text = ""
        for tenant in recent_tenants:
            tenants_text += f"• {tenant.name} - {tenant.mobile} - {tenant.status}\n"
        res['recent_tenants'] = tenants_text or "No recent tenants"
        
        return res

    # Today's Stats
    today_collections = fields.Float('Today Collections')
    today_collections_count = fields.Integer('Today Collections Count')
    today_expenses = fields.Float('Today Expenses')
    today_expenses_count = fields.Integer('Today Expenses Count')
    today_profit = fields.Float('Today Profit')
    today_new_tenants = fields.Integer('Today New Tenants')
    today_vacant_rooms = fields.Integer('Vacant Rooms Today')

    # Weekly Stats
    week_collections = fields.Float('This Week Collections')
    week_collections_count = fields.Integer('This Week Collections Count')
    week_expenses = fields.Float('This Week Expenses')
    week_expenses_count = fields.Integer('This Week Expenses Count')
    week_profit = fields.Float('This Week Profit')
    week_new_tenants = fields.Integer('This Week New Tenants')

    # Monthly Stats
    month_collections = fields.Float('This Month Collections')
    month_collections_count = fields.Integer('This Month Collections Count')
    month_new_tenants = fields.Integer('This Month New Tenants')
    month_expenses = fields.Float('This Month Expenses')
    month_expenses_count = fields.Integer('This Month Expenses Count')
    month_profit = fields.Float('This Month Profit')

    # Overall Stats
    total_properties = fields.Integer('Total Properties')
    total_rooms = fields.Integer('Total Rooms')
    occupied_rooms = fields.Integer('Occupied Rooms')
    vacant_rooms = fields.Integer('Vacant Rooms')
    occupancy_rate = fields.Float('Occupancy Rate (%)')
    total_tenants = fields.Integer('Total Active Tenants')
    
    # Agent Stats
    total_agents = fields.Integer('Total Agents')
    active_agents = fields.Integer('Active Agents')
    agents_with_tenants = fields.Integer('Agents with Tenants')
    top_agents_list = fields.Text('Top Performing Agents')
    agent_performance_summary = fields.Text('Agent Performance Summary')

    # Recent Activities
    recent_collections = fields.Text('Recent Collections')
    recent_tenants = fields.Text('Recent Tenants')
    
    # Statement and Outstanding Dues Stats
    total_outstanding_amount = fields.Float('Total Outstanding Amount')
    total_outstanding_count = fields.Integer('Tenants with Outstanding Dues')
    overdue_tenants_count = fields.Integer('Overdue Tenants')
    overdue_amount = fields.Float('Overdue Amount')
    critical_overdue_count = fields.Integer('Critical Overdue Count')
    critical_overdue_amount = fields.Float('Critical Overdue Amount')
    
    # Monthly Statement Analysis
    month_statement_entries = fields.Integer('Monthly Statement Entries')
    month_total_debits = fields.Float('Monthly Total Charges')
    month_total_credits = fields.Float('Monthly Total Payments')
    month_net_balance = fields.Float('Monthly Net Balance')
    collection_efficiency = fields.Float('Collection Efficiency %')
    
    # Tenant Balance Analysis
    tenants_with_negative_balance = fields.Integer('Tenants with Credit Balance')
    tenants_with_positive_balance = fields.Integer('Tenants with Debit Balance')
    top_debtors_list = fields.Text('Top Debtors List')

    def action_open_collections(self):
        return {
            'name': 'Collections',
            'type': 'ir.actions.act_window',
            'res_model': 'property.collection',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_properties(self):
        return {
            'name': 'Properties',
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'view_mode': 'kanban,list,form',
            'target': 'current',
        }

    def action_open_tenants(self):
        return {
            'name': 'Tenants',
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenant',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_rooms(self):
        return {
            'name': 'Rooms',
            'type': 'ir.actions.act_window',
            'res_model': 'property.room',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_open_vacant_rooms(self):
        return {
            'name': 'Vacant Rooms',
            'type': 'ir.actions.act_window',
            'res_model': 'property.room',
            'view_mode': 'list,form',
            'domain': [('status', '=', 'vacant')],
            'target': 'current',
        }
    
    def action_open_agents(self):
        return {
            'name': 'Property Agents',
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('is_company', '=', False), 
                      '|', ('category_id.name', 'in', ['Property Agent', 'Rental Agent', 'Sales Agent']),
                      ('function', 'ilike', 'agent')],
            'target': 'current',
        }
    
    def action_open_agent_agreements(self):
        return {
            'name': 'Agreements by Agent',
            'type': 'ir.actions.act_window',
            'res_model': 'property.agreement',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'active'), ('agent_id', '!=', False)],
            'context': {'group_by': 'agent_id'},
            'target': 'current',
        }
    
    def action_open_outstanding_dues(self):
        return {
            'name': 'Outstanding Dues',
            'type': 'ir.actions.act_window',
            'res_model': 'property.outstanding.dues',
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    def action_open_overdue_tenants(self):
        return {
            'name': 'Overdue Tenants',
            'type': 'ir.actions.act_window',
            'res_model': 'property.outstanding.dues',
            'view_mode': 'list,form',
            'domain': [('status', 'in', ['overdue_30', 'overdue_60', 'overdue_90', 'overdue_90plus', 'critical'])],
            'target': 'current',
        }
    
    def action_open_critical_overdue(self):
        return {
            'name': 'Critical Overdue',
            'type': 'ir.actions.act_window',
            'res_model': 'property.outstanding.dues',
            'view_mode': 'list,form',
            'domain': [('status', 'in', ['overdue_90', 'overdue_90plus', 'critical'])],
            'target': 'current',
        }
    
    def action_open_statement_analysis(self):
        return {
            'name': 'Statement Analysis',
            'type': 'ir.actions.act_window',
            'res_model': 'property.statement',
            'view_mode': 'pivot,graph,list,form',
            'target': 'current',
        }
    
    def action_open_tenant_balances(self):
        return {
            'name': 'Tenant Balances',
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenant',
            'view_mode': 'list,form',
            'context': {'search_default_active': 1},
            'target': 'current',
        }
