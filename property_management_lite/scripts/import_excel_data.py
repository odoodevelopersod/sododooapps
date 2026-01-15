#!/usr/bin/env python3
"""
Import Property Management Data from Excel Files
This script imports properties, flats, rooms, tenants, and agreements from Excel files.
"""

import pandas as pd
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def clean_value(val):
    """Clean and normalize values"""
    if pd.isna(val) or val == '' or val == 'NaN':
        return None
    if isinstance(val, str):
        return val.strip()
    return val

def parse_rent(rent_str):
    """Parse rent amount from string"""
    if pd.isna(rent_str):
        return 0.0
    try:
        # Remove any non-numeric characters except decimal point and minus
        rent_str = str(rent_str).replace(',', '').strip()
        return float(rent_str)
    except:
        return 0.0

def parse_deposit(deposit_str):
    """Parse deposit amount, handling special cases like (1000-500)"""
    if pd.isna(deposit_str):
        return 0.0
    try:
        deposit_str = str(deposit_str).strip()
        # Handle cases like (1000-500)
        if '(' in deposit_str and '-' in deposit_str:
            deposit_str = deposit_str.replace('(', '').replace(')', '')
            parts = deposit_str.split('-')
            return float(parts[0]) - float(parts[1])
        return float(deposit_str.replace(',', ''))
    except:
        return 0.0

def normalize_room_type(room_type):
    """Normalize room type to match system values"""
    if pd.isna(room_type):
        return 'single'
    
    room_type = str(room_type).upper().strip()
    
    # Mapping based on common patterns
    if 'ATTACH' in room_type:
        return 'attached'
    elif 'SHARING' in room_type or 'SHARED' in room_type:
        return 'shared'
    elif 'MAID' in room_type:
        return 'single'
    elif 'PART' in room_type or 'PARTITION' in room_type:
        return 'shared'
    elif 'SEPARATE' in room_type:
        return 'single'
    else:
        return 'single'

def import_excel_data(file_path):
    """Import data from Excel file"""
    print(f"\n{'='*80}")
    print(f"Importing data from: {file_path}")
    print(f"{'='*80}\n")
    
    # Read Excel file
    df = pd.read_excel(file_path, header=0)
    
    # Rename columns for easier access
    df.columns = ['building_name', 'flat_no', 'room_no', 'room_type', 'customer_name', 
                  'rent', 'deposit', 'deposit_transfer', 'parking_or_other', 
                  'other_charges', 'collected_by', 'payment_method', 'date'][:len(df.columns)]
    
    # Remove the header row if it exists
    df = df[df['building_name'] != 'BUILDING NAME']
    
    # Data structures to hold unique records
    properties = {}
    flats = {}
    rooms = []
    tenants = {}
    agreements = []
    
    # Process each row
    for idx, row in df.iterrows():
        building_name = clean_value(row['building_name'])
        flat_no = clean_value(row['flat_no'])
        room_type = clean_value(row['room_type'])
        customer_name = clean_value(row['customer_name'])
        rent = parse_rent(row['rent'])
        deposit = parse_deposit(row['deposit'])
        
        # Skip rows without essential data
        if not building_name or not flat_no:
            continue
        
        # 1. Create/Update Property
        if building_name not in properties:
            properties[building_name] = {
                'name': building_name,
                'code': building_name[:10].upper().replace(' ', '_'),
                'property_type': 'apartment',
                'address': f'{building_name}, Deira, Dubai',
            }
        
        # 2. Create/Update Flat
        flat_key = f"{building_name}_{flat_no}"
        if flat_key not in flats:
            # Extract floor from flat number (e.g., 102 -> floor 1, 305 -> floor 3)
            floor_num = 0
            try:
                flat_str = str(flat_no)
                if flat_str.isdigit() and len(flat_str) >= 2:
                    floor_num = int(flat_str[0]) if len(flat_str) == 2 else int(flat_str[:-2])
                else:
                    floor_num = 0  # Ground floor for non-numeric flats
            except:
                floor_num = 0
            
            flats[flat_key] = {
                'property_name': building_name,
                'flat_number': str(flat_no),
                'name': f"Flat {flat_no}",
                'floor': floor_num,
                'flat_type': '2bhk',  # Default type, can be updated later
            }
        
        # 3. Create Room (if room_type and customer exist)
        if room_type and customer_name:
            room_number = f"{flat_no}_{room_type[:10].replace(' ', '_')}"
            room_data = {
                'property_name': building_name,
                'flat_number': str(flat_no),
                'room_number': room_number,
                'room_type': normalize_room_type(room_type),
                'rent_amount': rent,
                'deposit_amount': deposit,
                'status': 'occupied' if customer_name else 'vacant',
            }
            rooms.append(room_data)
            
            # 4. Create Tenant
            if customer_name and customer_name not in tenants:
                # Generate a placeholder mobile number based on tenant name hash
                customer_name_str = str(customer_name)
                mobile_suffix = str(abs(hash(customer_name_str)) % 10000000).zfill(7)
                email_safe_name = customer_name_str.lower().replace(" ", ".").replace("'", "").replace('"', '')
                tenants[customer_name] = {
                    'name': customer_name_str,
                    'status': 'active',
                    'mobile': f'050{mobile_suffix}',  # Placeholder mobile
                    'phone': f'050{mobile_suffix}',   # Placeholder phone
                    'email': f'{email_safe_name}@placeholder.com',
                    'id_passport': f'ID{mobile_suffix}',  # Placeholder ID
                }
            
            # 5. Create Agreement
            if customer_name and rent > 0:
                agreement_data = {
                    'tenant_name': customer_name,
                    'property_name': building_name,
                    'flat_number': str(flat_no),
                    'room_number': room_number,
                    'rent_amount': rent,
                    'deposit_amount': deposit,
                    'start_date': '2025-08-01',  # Default start date
                    'end_date': '2026-07-31',   # Default end date (1 year)
                    'state': 'active',
                }
                agreements.append(agreement_data)
    
    # Print summary
    print(f"\n📊 Data Summary:")
    print(f"   Properties: {len(properties)}")
    print(f"   Flats: {len(flats)}")
    print(f"   Rooms: {len(rooms)}")
    print(f"   Tenants: {len(tenants)}")
    print(f"   Agreements: {len(agreements)}")
    
    return properties, flats, rooms, tenants, agreements

def generate_odoo_xml(properties, flats, rooms, tenants, agreements, output_file):
    """Generate Odoo XML data file"""
    print(f"\n📝 Generating Odoo XML file: {output_file}")
    
    xml_lines = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo>', '    <data noupdate="1">']
    
    # Generate Properties
    xml_lines.append('\n        <!-- Properties -->')
    for prop_name, prop_data in properties.items():
        prop_id = prop_data['code'].lower()
        xml_lines.append(f'        <record id="property_{prop_id}" model="property.property">')
        xml_lines.append(f'            <field name="name">{prop_data["name"]}</field>')
        xml_lines.append(f'            <field name="code">{prop_data["code"]}</field>')
        xml_lines.append(f'            <field name="property_type">{prop_data["property_type"]}</field>')
        xml_lines.append(f'            <field name="address">{prop_data["address"]}</field>')
        xml_lines.append(f'            <field name="state">active</field>')
        xml_lines.append('        </record>')
    
    # Generate Flats
    xml_lines.append('\n        <!-- Flats -->')
    for flat_key, flat_data in flats.items():
        prop_id = properties[flat_data['property_name']]['code'].lower()
        flat_id = f"{prop_id}_flat_{flat_data['flat_number']}"
        xml_lines.append(f'        <record id="flat_{flat_id}" model="property.flat">')
        xml_lines.append(f'            <field name="property_id" ref="property_{prop_id}"/>')
        xml_lines.append(f'            <field name="flat_number">{flat_data["flat_number"]}</field>')
        xml_lines.append('        </record>')
    
    # Generate Tenants
    xml_lines.append('\n        <!-- Tenants -->')
    for tenant_name, tenant_data in tenants.items():
        tenant_id = tenant_name.lower().replace(' ', '_').replace('.', '')[:50]
        xml_lines.append(f'        <record id="tenant_{tenant_id}" model="property.tenant">')
        xml_lines.append(f'            <field name="name">{tenant_name}</field>')
        xml_lines.append(f'            <field name="status">{tenant_data["status"]}</field>')
        xml_lines.append('        </record>')
    
    xml_lines.append('\n    </data>')
    xml_lines.append('</odoo>')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_lines))
    
    print(f"✅ XML file generated successfully!")

def generate_python_script(properties, flats, rooms, tenants, agreements, output_file):
    """Generate Python script for Odoo import"""
    print(f"\n📝 Generating Python import script: {output_file}")
    
    script_content = f'''# -*- coding: utf-8 -*-
"""
Odoo Data Import Script
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Run this script from Odoo shell:
    odoo-bin shell -d your_database -c your_config.conf
    >>> exec(open('scripts/odoo_import_data.py').read())
"""

from datetime import date, datetime

# Get environment
env = globals().get('env')
if not env:
    print("ERROR: This script must be run from Odoo shell")
    print("Usage: odoo-bin shell -d your_database")
    print("Then: exec(open('scripts/odoo_import_data.py').read())")
    exit(1)

print("\\n" + "="*80)
print("Starting Property Management Data Import")
print("="*80 + "\\n")

# Disable mail notifications during import
env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True))

# Statistics
stats = {{'properties': 0, 'flats': 0, 'rooms': 0, 'tenants': 0, 'agreements': 0}}

# 1. Import Properties
print("📦 Importing Properties...")
properties_map = {{}}

properties_data = {list(properties.values())}

for prop_data in properties_data:
    existing = env['property.property'].search([('name', '=', prop_data['name'])], limit=1)
    if existing:
        print(f"   ⚠️  Property already exists: {{prop_data['name']}}")
        properties_map[prop_data['name']] = existing
    else:
        prop = env['property.property'].create(prop_data)
        properties_map[prop_data['name']] = prop
        stats['properties'] += 1
        print(f"   ✅ Created property: {{prop_data['name']}}")

env.cr.commit()

# 2. Import Flats
print("\\n🏢 Importing Flats...")
flats_map = {{}}

flats_data = {list(flats.values())}

for flat_data in flats_data:
    prop = properties_map.get(flat_data['property_name'])
    if not prop:
        print(f"   ⚠️  Property not found for flat: {{flat_data['flat_number']}}")
        continue
    
    existing = env['property.flat'].search([
        ('property_id', '=', prop.id),
        ('flat_number', '=', flat_data['flat_number'])
    ], limit=1)
    
    if existing:
        flats_map[f"{{flat_data['property_name']}}_{{flat_data['flat_number']}}"] = existing
    else:
        flat = env['property.flat'].create({{
            'property_id': prop.id,
            'flat_number': flat_data['flat_number'],
            'floor': flat_data['floor'],
            'flat_type': flat_data['flat_type'],
        }})
        flats_map[f"{{flat_data['property_name']}}_{{flat_data['flat_number']}}"] = flat
        stats['flats'] += 1
        print(f"   ✅ Created flat: {{flat_data['flat_number']}} (Floor {{flat_data['floor']}}) in {{flat_data['property_name']}}")

env.cr.commit()

# 3. Import Room Types (if needed)
print("\\n🚪 Ensuring Room Types exist...")
room_types_needed = {set(room['room_type'] for room in rooms)}

room_type_codes = {{
    'single': 'SINGLE',
    'attached': 'ATTACH',
    'shared': 'SHARED'
}}

for rt_name in room_types_needed:
    existing = env['property.room.type'].search([('code', '=', room_type_codes.get(rt_name, rt_name.upper()))], limit=1)
    if not existing:
        env['property.room.type'].create({{
            'name': rt_name.title(),
            'code': room_type_codes.get(rt_name, rt_name.upper()),
            'default_rent': 0,
            'default_deposit': 0
        }})
        print(f"   ✅ Created room type: {{rt_name}}")

env.cr.commit()

# 4. Import Rooms
print("\\n🛏️  Importing Rooms...")
rooms_map = {{}}

rooms_data = {rooms}

for room_data in rooms_data:
    flat_key = f"{{room_data['property_name']}}_{{room_data['flat_number']}}"
    flat = flats_map.get(flat_key)
    
    if not flat:
        print(f"   ⚠️  Flat not found for room: {{room_data['room_number']}}")
        continue
    
    room_type = env['property.room.type'].search([('name', '=', room_data['room_type'])], limit=1)
    if not room_type:
        room_type = env['property.room.type'].search([], limit=1)
    
    existing = env['property.room'].search([
        ('flat_id', '=', flat.id),
        ('room_number', '=', room_data['room_number'])
    ], limit=1)
    
    if existing:
        rooms_map[f"{{flat_key}}_{{room_data['room_number']}}"] = existing
    else:
        room = env['property.room'].create({{
            'flat_id': flat.id,
            'property_id': flat.property_id.id,
            'room_number': room_data['room_number'],
            'room_type_id': room_type.id if room_type else False,
            'rent_amount': room_data['rent_amount'],
            'deposit_amount': room_data['deposit_amount'],
            'status': room_data['status'],
        }})
        rooms_map[f"{{flat_key}}_{{room_data['room_number']}}"] = room
        stats['rooms'] += 1
        print(f"   ✅ Created room: {{room_data['room_number']}} in flat {{room_data['flat_number']}}")

env.cr.commit()

# 5. Import Tenants
print("\\n👤 Importing Tenants...")
tenants_map = {{}}

tenants_data = {list(tenants.values())}

for tenant_data in tenants_data:
    existing = env['property.tenant'].search([('name', '=', tenant_data['name'])], limit=1)
    if existing:
        tenants_map[tenant_data['name']] = existing
        print(f"   ⚠️  Tenant already exists: {{tenant_data['name']}}")
    else:
        tenant = env['property.tenant'].create(tenant_data)
        tenants_map[tenant_data['name']] = tenant
        stats['tenants'] += 1
        print(f"   ✅ Created tenant: {{tenant_data['name']}}")

env.cr.commit()

# 6. Import Agreements
print("\\n📄 Importing Agreements...")

agreements_data = {agreements}

for agr_data in agreements_data:
    tenant = tenants_map.get(agr_data['tenant_name'])
    flat_key = f"{{agr_data['property_name']}}_{{agr_data['flat_number']}}"
    room_key = f"{{flat_key}}_{{agr_data['room_number']}}"
    room = rooms_map.get(room_key)
    
    if not tenant:
        print(f"   ⚠️  Tenant not found: {{agr_data['tenant_name']}}")
        continue
    
    if not room:
        print(f"   ⚠️  Room not found: {{agr_data['room_number']}}")
        continue
    
    # Check if agreement already exists for this tenant and room
    existing = env['property.agreement'].search([
        ('tenant_id', '=', tenant.id),
        ('room_id', '=', room.id),
        ('state', '=', 'active')
    ], limit=1)
    
    if existing:
        print(f"   ⚠️  Agreement already exists for {{tenant.name}} in room {{room.name}}")
        continue
    
    # Check if room is already occupied by another tenant
    room_occupied = env['property.agreement'].search([
        ('room_id', '=', room.id),
        ('state', '=', 'active')
    ], limit=1)
    
    if room_occupied:
        print(f"   ⚠️  Room {{room.name}} is already occupied by {{room_occupied.tenant_id.name}}, skipping {{tenant.name}}")
        continue
    
    # Parse dates if they are strings
    start_date = agr_data['start_date']
    end_date = agr_data['end_date']
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    agreement = env['property.agreement'].create({{
        'tenant_id': tenant.id,
        'room_id': room.id,
        'start_date': start_date,
        'end_date': end_date,
        'rent_amount': agr_data['rent_amount'],
        'deposit_amount': agr_data['deposit_amount'],
        'state': 'draft',  # Create as draft first
    }})
    
    # Activate the agreement
    agreement.action_activate()
    
    stats['agreements'] += 1
    print(f"   ✅ Created agreement: {{tenant.name}} - {{room.name}}")

env.cr.commit()

# Print final statistics
print("\\n" + "="*80)
print("Import Completed Successfully!")
print("="*80)
print(f"\\n📊 Final Statistics:")
print(f"   Properties created: {{stats['properties']}}")
print(f"   Flats created: {{stats['flats']}}")
print(f"   Rooms created: {{stats['rooms']}}")
print(f"   Tenants created: {{stats['tenants']}}")
print(f"   Agreements created: {{stats['agreements']}}")
print("\\n✅ All data imported successfully!\\n")
'''
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Python script generated successfully!")

if __name__ == '__main__':
    # Import from both files
    file1 = 'import_data_template_DEIRA_Aug25.xlsx'
    file2 = 'import_data_template_AUG2025_Complete.xlsx'
    
    # Import first file
    props1, flats1, rooms1, tenants1, agrs1 = import_excel_data(file1)
    
    # Import second file
    props2, flats2, rooms2, tenants2, agrs2 = import_excel_data(file2)
    
    # Merge data
    print(f"\n🔄 Merging data from both files...")
    all_properties = {**props1, **props2}
    all_flats = {**flats1, **flats2}
    all_rooms = rooms1 + rooms2
    all_tenants = {**tenants1, **tenants2}
    all_agreements = agrs1 + agrs2
    
    print(f"\n📊 Combined Data Summary:")
    print(f"   Total Properties: {len(all_properties)}")
    print(f"   Total Flats: {len(all_flats)}")
    print(f"   Total Rooms: {len(all_rooms)}")
    print(f"   Total Tenants: {len(all_tenants)}")
    print(f"   Total Agreements: {len(all_agreements)}")
    
    # Generate import script
    generate_python_script(all_properties, all_flats, all_rooms, all_tenants, all_agreements, 
                          'scripts/odoo_import_data.py')
    
    print(f"\n{'='*80}")
    print("✅ Import preparation completed!")
    print(f"{'='*80}")
    print("\nNext steps:")
    print("1. Review the generated script: scripts/odoo_import_data.py")
    print("2. Run from Odoo shell:")
    print("   odoo-bin shell -d your_database -c your_config.conf")
    print("   >>> exec(open('scripts/odoo_import_data.py').read())")
    print()
