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
from odoo.exceptions import UserError
import csv
import io
import base64
import logging

_logger = logging.getLogger(__name__)


class PropertyDataImportWizard(models.TransientModel):
    _name = 'property.data.import.wizard'
    _description = 'Property Management Data Import Wizard'

    state = fields.Selection([
        ('upload', 'Upload Files'),
        ('mapping', 'Field Mapping'),
        ('import', 'Import Data'),
        ('done', 'Completed')
    ], default='upload', string='State')

    # File upload fields
    properties_file = fields.Binary(string='Properties CSV File')
    flats_file = fields.Binary(string='Flats CSV File')
    rooms_file = fields.Binary(string='Rooms CSV File')
    tenants_file = fields.Binary(string='Tenants CSV File')
    agreements_file = fields.Binary(string='Agreements CSV File')

    # Import options
    update_existing = fields.Boolean(string='Update Existing Records', default=False)
    create_missing = fields.Boolean(string='Create Missing Records', default=True)

    # Import results
    import_log = fields.Text(string='Import Log', readonly=True)
    properties_created = fields.Integer(string='Properties Created', readonly=True)
    flats_created = fields.Integer(string='Flats Created', readonly=True)
    rooms_created = fields.Integer(string='Rooms Created', readonly=True)
    tenants_created = fields.Integer(string='Tenants Created', readonly=True)
    agreements_created = fields.Integer(string='Agreements Created', readonly=True)

    def action_start_import(self):
        """Start the import process"""
        self.state = 'import'
        return self._do_import()

    def _do_import(self):
        """Execute the complete import process"""
        log_lines = []
        
        try:
            # Import in the correct order to respect dependencies
            if self.properties_file:
                props_created = self._import_properties()
                self.properties_created = props_created
                log_lines.append(f"✓ Properties imported: {props_created}")

            if self.flats_file:
                flats_created = self._import_flats()
                self.flats_created = flats_created
                log_lines.append(f"✓ Flats imported: {flats_created}")

            if self.rooms_file:
                rooms_created = self._import_rooms()
                self.rooms_created = rooms_created
                log_lines.append(f"✓ Rooms imported: {rooms_created}")

            if self.tenants_file:
                tenants_created = self._import_tenants()
                self.tenants_created = tenants_created
                log_lines.append(f"✓ Tenants imported: {tenants_created}")

            if self.agreements_file:
                agreements_created = self._import_agreements()
                self.agreements_created = agreements_created
                log_lines.append(f"✓ Agreements imported: {agreements_created}")

            self.import_log = '\n'.join(log_lines)
            self.state = 'done'

            return {
                'name': 'Import Completed',
                'type': 'ir.actions.act_window',
                'res_model': 'property.data.import.wizard',
                'view_mode': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        except Exception as e:
            _logger.error(f"Import error: {str(e)}")
            raise UserError(f"Import failed: {str(e)}")

    def _parse_csv_file(self, file_data):
        """Parse CSV file and return rows as list of dictionaries"""
        if not file_data:
            return []
        
        decoded_data = base64.b64decode(file_data).decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded_data))
        return list(csv_reader)

    def _import_properties(self):
        """Import properties from CSV"""
        rows = self._parse_csv_file(self.properties_file)
        created_count = 0

        for row in rows:
            try:
                # Check if property already exists
                existing = self.env['property.property'].search([
                    ('name', '=', row['name'])
                ])

                if existing and not self.update_existing:
                    continue

                vals = {
                    'name': row['name'],
                    'address': row.get('address', ''),
                    'property_type': row.get('property_type', 'building'),
                }

                if existing and self.update_existing:
                    existing.write(vals)
                else:
                    self.env['property.property'].create(vals)
                    created_count += 1

            except Exception as e:
                _logger.warning(f"Error importing property {row.get('name', 'Unknown')}: {str(e)}")
                continue

        return created_count

    def _import_flats(self):
        """Import flats from CSV"""
        rows = self._parse_csv_file(self.flats_file)
        created_count = 0

        for row in rows:
            try:
                # Find parent property
                property_name = row.get('property_external_id', '').replace('property_', '').replace('_', ' ').upper()
                property_record = self.env['property.property'].search([
                    ('name', 'ilike', property_name)
                ], limit=1)

                if not property_record:
                    _logger.warning(f"Property not found for flat: {row.get('name', 'Unknown')}")
                    continue

                # Check if flat already exists
                existing = self.env['property.flat'].search([
                    ('property_id', '=', property_record.id),
                    ('flat_number', '=', row.get('flat_number', ''))
                ])

                if existing and not self.update_existing:
                    continue

                vals = {
                    'name': row['name'],
                    'property_id': property_record.id,
                    'flat_number': row.get('flat_number', ''),
                }

                if existing and self.update_existing:
                    existing.write(vals)
                else:
                    self.env['property.flat'].create(vals)
                    created_count += 1

            except Exception as e:
                _logger.warning(f"Error importing flat {row.get('name', 'Unknown')}: {str(e)}")
                continue

        return created_count

    def _import_rooms(self):
        """Import rooms from CSV"""
        rows = self._parse_csv_file(self.rooms_file)
        created_count = 0

        for row in rows:
            try:
                # Parse flat external ID to find parent flat
                flat_external_id = row.get('flat_external_id', '')
                parts = flat_external_id.replace('property_', '').split('_flat_')
                
                if len(parts) != 2:
                    continue
                    
                property_name = parts[0].replace('_', ' ').upper()
                flat_number = parts[1]

                # Find parent flat
                flat_record = self.env['property.flat'].search([
                    ('property_id.name', 'ilike', property_name),
                    ('flat_number', '=', flat_number)
                ], limit=1)

                if not flat_record:
                    _logger.warning(f"Flat not found for room: {row.get('name', 'Unknown')}")
                    continue

                # Check if room already exists
                existing = self.env['property.room'].search([
                    ('flat_id', '=', flat_record.id),
                    ('name', '=', row.get('name', ''))
                ])

                if existing and not self.update_existing:
                    continue

                # Map room type
                room_type_mapping = {
                    'attached_bathroom': 'attached',
                    'shared': 'shared',
                    'maid_room': 'single',
                    'hall_partition': 'shared',
                    'partition': 'shared',
                    'other': 'single'
                }

                vals = {
                    'name': row['name'],
                    'flat_id': flat_record.id,
                    'room_type': room_type_mapping.get(row.get('room_type_standard', 'single'), 'single'),
                }

                if existing and self.update_existing:
                    existing.write(vals)
                else:
                    self.env['property.room'].create(vals)
                    created_count += 1

            except Exception as e:
                _logger.warning(f"Error importing room {row.get('name', 'Unknown')}: {str(e)}")
                continue

        return created_count

    def _import_tenants(self):
        """Import tenants from CSV"""
        rows = self._parse_csv_file(self.tenants_file)
        created_count = 0

        for row in rows:
            try:
                # Check if tenant already exists
                existing = self.env['property.tenant'].search([
                    ('name', '=', row['name'])
                ])

                if existing and not self.update_existing:
                    continue

                vals = {
                    'name': row['name'],
                    'status': row.get('status', 'active'),
                    'nationality': row.get('nationality', ''),
                }

                if existing and self.update_existing:
                    existing.write(vals)
                else:
                    self.env['property.tenant'].create(vals)
                    created_count += 1

            except Exception as e:
                _logger.warning(f"Error importing tenant {row.get('name', 'Unknown')}: {str(e)}")
                continue

        return created_count

    def _import_agreements(self):
        """Import rental agreements from CSV"""
        rows = self._parse_csv_file(self.agreements_file)
        created_count = 0

        for row in rows:
            try:
                # Find tenant
                tenant_name = row.get('tenant_external_id', '').replace('tenant_', '').replace('_', ' ').title()
                tenant_record = self.env['property.tenant'].search([
                    ('name', '=', tenant_name)
                ], limit=1)

                if not tenant_record:
                    _logger.warning(f"Tenant not found for agreement: {row.get('name', 'Unknown')}")
                    continue

                # Find room
                room_external_id = row.get('room_external_id', '')
                # Parse: property_adcb_flat_105_room_105
                parts = room_external_id.replace('property_', '').split('_')
                
                if len(parts) < 5:
                    continue
                    
                property_name = parts[0].replace('_', ' ').upper()
                flat_number = parts[2]
                room_number = parts[4]

                room_record = self.env['property.room'].search([
                    ('flat_id.property_id.name', 'ilike', property_name),
                    ('flat_id.flat_number', '=', flat_number),
                    ('name', 'ilike', f'Room {room_number}')
                ], limit=1)

                if not room_record:
                    _logger.warning(f"Room not found for agreement: {row.get('name', 'Unknown')}")
                    continue

                # Check if agreement already exists
                existing = self.env['property.agreement'].search([
                    ('tenant_id', '=', tenant_record.id),
                    ('room_id', '=', room_record.id)
                ])

                if existing and not self.update_existing:
                    continue

                vals = {
                    'tenant_id': tenant_record.id,
                    'room_id': room_record.id,
                    'rent_amount': float(row.get('rent_amount', 0)) if row.get('rent_amount') else 0,
                    'deposit_amount': float(row.get('deposit_amount', 0)) if row.get('deposit_amount') else 0,
                    'start_date': row.get('start_date', '2025-08-01'),
                    'end_date': row.get('end_date', '2026-07-31'),
                    'state': row.get('state', 'active'),
                }

                if existing and self.update_existing:
                    existing.write(vals)
                else:
                    self.env['property.agreement'].create(vals)
                    created_count += 1

            except Exception as e:
                _logger.warning(f"Error importing agreement {row.get('name', 'Unknown')}: {str(e)}")
                continue

        return created_count

    def action_restart(self):
        """Restart the wizard"""
        self.state = 'upload'
        self.import_log = False
        self.properties_created = 0
        self.flats_created = 0
        self.rooms_created = 0
        self.tenants_created = 0
        self.agreements_created = 0
        
        return {
            'name': 'Property Data Import',
            'type': 'ir.actions.act_window',
            'res_model': 'property.data.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }