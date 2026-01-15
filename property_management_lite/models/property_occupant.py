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


class PropertyOccupant(models.Model):
    _name = 'property.occupant'
    _description = 'Room Occupant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'is_primary desc, name'

    # Basic Information
    name = fields.Char('Full Name', required=True, tracking=True)
    occupant_type = fields.Selection([
        ('primary', 'Primary Tenant'),
        ('co_tenant', 'Co-Tenant'),
        ('spouse', 'Spouse'),
        ('dependent', 'Dependent'),
        ('guest', 'Long-term Guest'),
    ], string='Occupant Type', default='co_tenant', required=True, tracking=True)
    is_primary = fields.Boolean('Primary Tenant', default=False, tracking=True,
                                help="Check this if this person is the primary tenant responsible for payments")
    
    # Relations
    agreement_id = fields.Many2one('property.agreement', 'Agreement', required=True, 
                                   ondelete='cascade', tracking=True)
    tenant_id = fields.Many2one(related='agreement_id.tenant_id', string='Main Tenant', 
                               store=True, readonly=True)
    room_id = fields.Many2one(related='agreement_id.room_id', string='Room', 
                             store=True, readonly=True)
    property_id = fields.Many2one(related='agreement_id.property_id', string='Property', 
                                  store=True, readonly=True)
    
    # Contact Information
    mobile = fields.Char('Mobile Number', tracking=True)
    phone = fields.Char('Phone Number', tracking=True)
    email = fields.Char('Email', tracking=True)
    
    # Identification
    id_passport = fields.Char('ID/Passport Number', tracking=True)
    id_type = fields.Selection([
        ('emirates_id', 'Emirates ID'),
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('other', 'Other'),
    ], string='ID Type', default='emirates_id')
    
    # Personal Information
    nationality = fields.Many2one('res.country', 'Nationality')
    date_of_birth = fields.Date('Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Gender')
    
    # Emergency Contact
    emergency_contact_name = fields.Char('Emergency Contact Name')
    emergency_contact_phone = fields.Char('Emergency Contact Phone')
    emergency_contact_relation = fields.Char('Relation')
    
    # Professional Information
    company_name = fields.Char('Company Name')
    job_title = fields.Char('Job Title')
    
    # Dates
    move_in_date = fields.Date('Move In Date', default=fields.Date.today)
    move_out_date = fields.Date('Move Out Date')
    
    # Documents
    document_ids = fields.One2many('ir.attachment', 'res_id', 'Documents',
                                   domain=[('res_model', '=', 'property.occupant')])
    documents_count = fields.Integer('Documents', compute='_compute_documents_count')
    
    # Status
    active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')
    
    # Image
    image = fields.Image('Photo', max_width=1920, max_height=1920)
    image_medium = fields.Image('Medium Image', related='image', max_width=128, max_height=128, store=True)
    
    @api.depends('document_ids')
    def _compute_documents_count(self):
        for record in self:
            record.documents_count = len(record.document_ids)
    
    @api.constrains('is_primary', 'agreement_id')
    def _check_single_primary(self):
        """Ensure only one primary occupant per agreement"""
        for record in self:
            if record.is_primary:
                other_primary = self.search([
                    ('agreement_id', '=', record.agreement_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', record.id)
                ])
                if other_primary:
                    raise ValidationError(_(
                        'Only one primary tenant is allowed per agreement. '
                        'Please uncheck the primary flag on %s first.'
                    ) % other_primary[0].name)
    
    @api.constrains('id_passport')
    def _check_id_passport_unique(self):
        """Check if ID/Passport is unique"""
        for record in self:
            if record.id_passport:
                existing = self.search([
                    ('id_passport', '=', record.id_passport),
                    ('id', '!=', record.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_(
                        'ID/Passport number %s is already registered for %s!'
                    ) % (record.id_passport, existing[0].name))
    
    @api.model
    def create(self, vals):
        """Auto-set occupant_type to primary if is_primary is True"""
        if vals.get('is_primary'):
            vals['occupant_type'] = 'primary'
        return super().create(vals)
    
    def write(self, vals):
        """Auto-set occupant_type to primary if is_primary is True"""
        if vals.get('is_primary'):
            vals['occupant_type'] = 'primary'
        return super().write(vals)
    
    def action_view_documents(self):
        """Open documents view"""
        self.ensure_one()
        return {
            'name': _('Occupant Documents'),
            'view_mode': 'kanban,list,form',
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'domain': [('res_model', '=', 'property.occupant'), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': 'property.occupant',
                'default_res_id': self.id,
            }
        }
    
    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.is_primary:
                name = f"★ {name} (Primary)"
            elif record.occupant_type:
                name = f"{name} ({dict(record._fields['occupant_type'].selection).get(record.occupant_type)})"
            result.append((record.id, name))
        return result
