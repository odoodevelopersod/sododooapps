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


class PropertyOtherCharges(models.Model):
    _name = 'property.other.charges'
    _description = 'Other Charges Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'charge_type, name'

    name = fields.Char('Charge Name', required=True, tracking=True)
    charge_type = fields.Selection([
        ('utility', 'Utility Charges'),
        ('maintenance', 'Maintenance Charges'),
        ('service', 'Service Charges'),
        ('amenity', 'Amenity Charges'),
        ('penalty', 'Penalty/Fine'),
        ('insurance', 'Insurance'),
        ('cleaning', 'Cleaning Charges'),
        ('internet', 'Internet Charges'),
        ('cable_tv', 'Cable TV'),
        ('laundry', 'Laundry Services'),
        ('gym', 'Gym Membership'),
        ('other', 'Other'),
    ], string='Charge Type', required=True, default='other', tracking=True)
    
    amount = fields.Monetary('Amount', required=True, currency_field='currency_id', tracking=True)
    
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'), 
        ('yearly', 'Yearly'),
        ('one_time', 'One Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], string='Frequency', required=True, default='monthly', tracking=True)
    
    description = fields.Text('Description')
    is_mandatory = fields.Boolean('Mandatory', default=False, 
                                 help="If checked, this charge will be automatically applied to all applicable agreements")
    
    # Relations
    property_ids = fields.Many2many('property.property', string='Applicable Properties',
                                   help="Leave empty to apply to all properties")
    room_type_ids = fields.Many2many('property.room.type', string='Applicable Room Types',
                                    help="Leave empty to apply to all room types")
    
    # Financial
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                  default=lambda self: self.env.company.currency_id)
    
    # Archive
    active = fields.Boolean('Active', default=True)
    
    # Computed
    agreement_charge_ids = fields.One2many('property.agreement.charges', 'charge_id', 'Agreement Charges')
    agreements_count = fields.Integer('Applied Agreements', compute='_compute_agreements_count')
    
    @api.depends('agreement_charge_ids', 'agreement_charge_ids.active')
    def _compute_agreements_count(self):
        for record in self:
            active_charges = record.agreement_charge_ids.filtered('active')
            record.agreements_count = len(active_charges.mapped('agreement_id'))
    
    def action_view_agreements(self):
        active_charges = self.agreement_charge_ids.filtered('active')
        agreement_ids = active_charges.mapped('agreement_id').ids
        return {
            'name': _('Applied Agreements'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.agreement',
            'view_mode': 'list,form',
            'domain': [('id', 'in', agreement_ids)],
            'context': {'search_default_active': 1}
        }
    
    @api.constrains('amount')
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_('Charge amount must be positive!'))


class PropertyAgreementCharges(models.Model):
    _name = 'property.agreement.charges'
    _description = 'Agreement Other Charges'
    _order = 'agreement_id, charge_id'

    agreement_id = fields.Many2one('property.agreement', 'Agreement', required=True, ondelete='cascade')
    charge_id = fields.Many2one('property.other.charges', 'Charge', required=True, ondelete='cascade')
    
    # Override amount if needed
    amount = fields.Monetary('Amount', currency_field='currency_id')
    custom_amount = fields.Boolean('Custom Amount', default=False)
    
    # Dates
    start_date = fields.Date('Start Date', default=fields.Date.today)
    end_date = fields.Date('End Date')
    
    # Status
    active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')
    
    # Related fields for easy access
    charge_name = fields.Char(related='charge_id.name', string='Charge Name', store=True)
    charge_type = fields.Selection(related='charge_id.charge_type', string='Charge Type', store=True)
    frequency = fields.Selection(related='charge_id.frequency', string='Frequency', store=True)
    default_amount = fields.Monetary(related='charge_id.amount', string='Default Amount', store=True)
    
    # Financial
    currency_id = fields.Many2one(related='agreement_id.currency_id', string='Currency')
    
    @api.onchange('charge_id')
    def _onchange_charge_id(self):
        if self.charge_id:
            if not self.custom_amount:
                self.amount = self.charge_id.amount
    
    @api.onchange('custom_amount')
    def _onchange_custom_amount(self):
        if not self.custom_amount and self.charge_id:
            self.amount = self.charge_id.amount
    
    @api.model
    def create(self, vals):
        # Set default amount if not custom
        if not vals.get('custom_amount') and vals.get('charge_id'):
            charge = self.env['property.other.charges'].browse(vals['charge_id'])
            if not vals.get('amount'):
                vals['amount'] = charge.amount
        return super().create(vals)
    
    def write(self, vals):
        # Update amount if custom_amount is disabled
        if 'custom_amount' in vals and not vals['custom_amount']:
            for record in self:
                if record.charge_id:
                    vals['amount'] = record.charge_id.amount
        return super().write(vals)