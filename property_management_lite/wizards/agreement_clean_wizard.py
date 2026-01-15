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
from odoo.exceptions import UserError


class PropertyAgreementCleanWizard(models.TransientModel):
    _name = 'property.agreement.clean.wizard'
    _description = 'Agreement Clean & Terminate Wizard'
    
    agreement_id = fields.Many2one('property.agreement', 'Agreement', required=True)
    agreement_name = fields.Char('Agreement', readonly=True)
    
    # Summary counts
    statement_count = fields.Integer('Statements', compute='_compute_counts')
    invoice_count = fields.Integer('Invoices', compute='_compute_counts')
    collection_count = fields.Integer('Collections', compute='_compute_counts')
    payment_count = fields.Integer('Payments', compute='_compute_counts')
    
    @api.depends('agreement_id')
    def _compute_counts(self):
        for record in self:
            if record.agreement_id:
                record.statement_count = self.env['property.statement'].search_count([
                    ('agreement_id', '=', record.agreement_id.id)
                ])
                record.invoice_count = self.env['account.move'].search_count([
                    ('agreement_id', '=', record.agreement_id.id)
                ])
                record.collection_count = self.env['property.collection'].search_count([
                    ('agreement_id', '=', record.agreement_id.id)
                ])
                
                # Count payments from collections
                collections = self.env['property.collection'].search([
                    ('agreement_id', '=', record.agreement_id.id),
                    ('payment_id', '!=', False)
                ])
                record.payment_count = len(collections.mapped('payment_id'))
            else:
                record.statement_count = 0
                record.invoice_count = 0
                record.collection_count = 0
                record.payment_count = 0
    
    def action_confirm_clean_terminate(self):
        """Execute the cleanup and termination"""
        self.ensure_one()
        
        if not self.agreement_id:
            raise UserError(_("Agreement not found!"))
        
        agreement = self.agreement_id
        
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f"Starting clean & terminate for agreement: {agreement.name}")
        
        # 1. Delete statements
        statements = self.env['property.statement'].search([
            ('agreement_id', '=', agreement.id)
        ])
        if statements:
            _logger.info(f"Deleting {len(statements)} statement entries...")
            statements.sudo().unlink()
        
        # 2. Delete payments (via collections)
        collections =self.env['property.collection'].search([
            ('agreement_id', '=', agreement.id),
            ('payment_id', '!=', False)
        ])
        if collections:
            _logger.info(f"Deleting {len(collections)} payments...")
            for collection in collections:
                if collection.payment_id:
                    payment_id = collection.payment_id.id
                    # Use SQL to bypass validation
                    self.env.cr.execute("DELETE FROM account_payment WHERE id = %s", (payment_id,))
        
        # 3. Delete invoices
        invoices = self.env['account.move'].search([
            ('agreement_id', '=', agreement.id)
        ])
        if invoices:
            _logger.info(f"Deleting {len(invoices)} invoices...")
            # Cancel first if posted
            posted_invoices = invoices.filtered(lambda inv: inv.state == 'posted')
            if posted_invoices:
                posted_invoices.button_draft()
                posted_invoices.button_cancel()
            invoices.sudo().unlink()
        
        # 4. Delete collections
        collections_all = self.env['property.collection'].search([
            ('agreement_id', '=', agreement.id)
        ])
        if collections_all:
            _logger.info(f"Deleting {len(collections_all)} collection records...")
            collections_all.sudo().unlink()
        
        # 5. Terminate the agreement
        _logger.info(f"Terminating agreement: {agreement.name}")
        agreement.action_terminate()
        
        _logger.info(f"Clean & terminate completed for agreement: {agreement.name}")
        
        # Show notification and close wizard
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Agreement cleaned and terminated successfully!'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
    
    def action_cancel(self):
        """Cancel the wizard"""
        return {'type': 'ir.actions.act_window_close'}
