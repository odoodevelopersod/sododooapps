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


class PropertyStatementWizard(models.TransientModel):
    _name = 'property.statement.wizard'
    _description = 'Statement Report Generator'

    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True)
    date_from = fields.Date(string='From Date', required=True, 
                           default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='To Date', required=True, default=fields.Date.today)
    
    report_type = fields.Selection([
        ('detailed', 'Detailed Statement'),
        ('summary', 'Summary Only'),
    ], string='Report Type', default='detailed', required=True)
    
    include_zero_transactions = fields.Boolean(string='Include Zero Amount Transactions', default=False)

    def action_generate_report(self):
        """Generate and display the statement report"""
        self.ensure_one()
        
        domain = [
            ('tenant_id', '=', self.tenant_id.id),
            ('transaction_date', '>=', self.date_from),
            ('transaction_date', '<=', self.date_to),
        ]
        
        if not self.include_zero_transactions:
            domain.append('|')
            domain.append(('debit_amount', '!=', 0))
            domain.append(('credit_amount', '!=', 0))
        
        if self.report_type == 'detailed':
            return {
                'name': f'Statement - {self.tenant_id.name} ({self.date_from} to {self.date_to})',
                'type': 'ir.actions.act_window',
                'res_model': 'property.statement',
                'view_mode': 'list',
                'domain': domain,
                'context': {
                    'search_default_tenant_id': self.tenant_id.id,
                },
                'target': 'current',
            }
        else:
            # Summary report - return pivot view
            return {
                'name': f'Statement Summary - {self.tenant_id.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'property.statement',
                'view_mode': 'pivot,graph',
                'domain': domain,
                'context': {
                    'search_default_tenant_id': self.tenant_id.id,
                },
                'target': 'current',
            }