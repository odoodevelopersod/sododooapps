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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Property Management Categories
    is_tenant = fields.Boolean('Is Tenant')
    is_landlord = fields.Boolean('Is Landlord')
    is_property_vendor = fields.Boolean('Is Property Vendor')
    
    # Tenant Information
    tenant_id = fields.Many2one('property.tenant', 'Tenant Profile')
    current_room_id = fields.Many2one('property.room', 'Current Room')
    tenant_status = fields.Selection(related='tenant_id.status', string='Tenant Status')
    
    # Landlord Information
    owned_properties = fields.One2many('property.property', 'landlord_id', 'Owned Properties')
    properties_count = fields.Integer('Properties Count', compute='_compute_properties_count')
    
    # Collections & Payments
    collection_ids = fields.One2many('property.collection', 'tenant_id', 'Collections')
    total_paid = fields.Monetary('Total Paid', compute='_compute_payment_stats', currency_field='currency_id')
    last_payment_date = fields.Date('Last Payment', compute='_compute_payment_stats')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.company.currency_id)
    
    @api.depends('owned_properties')
    def _compute_properties_count(self):
        for partner in self:
            partner.properties_count = len(partner.owned_properties)
    
    @api.depends('collection_ids.amount_collected')
    def _compute_payment_stats(self):
        for partner in self:
            if partner.is_tenant and partner.tenant_id:
                partner.total_paid = sum(partner.collection_ids.mapped('amount_collected'))
                partner.last_payment_date = max(partner.collection_ids.mapped('date')) if partner.collection_ids else False
            else:
                partner.total_paid = 0
                partner.last_payment_date = False
    
    def action_view_properties(self):
        return {
            'name': 'Properties',
            'view_mode': 'list,form',
            'res_model': 'property.property',
            'type': 'ir.actions.act_window',
            'domain': [('landlord_id', '=', self.id), ('active', '=', True)],
            'context': {'default_landlord_id': self.id}
        }
    
    def action_view_collections(self):
        return {
            'name': 'Collections',
            'view_mode': 'list,form',
            'res_model': 'property.collection',
            'type': 'ir.actions.act_window',
            'domain': [('tenant_id', '=', self.tenant_id.id), ('active', '=', True)],
        }
    
    def action_create_tenant_profile(self):
        tenant_vals = {
            'name': self.name,
            'mobile': self.mobile,
            'email': self.email,
            'partner_id': self.id,
        }
        tenant = self.env['property.tenant'].create(tenant_vals)
        self.write({
            'is_tenant': True,
            'tenant_id': tenant.id,
        })
        
        return {
            'name': 'Tenant Profile',
            'view_mode': 'form',
            'res_model': 'property.tenant',
            'res_id': tenant.id,
            'type': 'ir.actions.act_window',
        }
