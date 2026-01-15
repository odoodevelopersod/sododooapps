# -*- coding: utf-8 -*-
"""
Odoo Data Import Script - Safe Version with Transaction Handling
Generated on: 2025-11-19

Run this script from Odoo shell:
    odoo-bin shell -d your_database -c your_config.conf
    >>> exec(open('scripts/odoo_import_data_safe.py').read())
"""

from datetime import date

# Get environment
env = globals().get('env')
if not env:
    print("ERROR: This script must be run from Odoo shell")
    print("Usage: odoo-bin shell -d your_database")
    print("Then: exec(open('scripts/odoo_import_data_safe.py').read())")
    exit(1)

print("\n" + "="*80)
print("Starting Property Management Data Import")
print("="*80 + "\n")

# Rollback any failed transaction first
try:
    env.cr.rollback()
    print("✅ Rolled back any previous failed transactions\n")
except:
    pass

# Disable mail notifications during import
env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True))

# Statistics
stats = {'properties': 0, 'flats': 0, 'rooms': 0, 'tenants': 0, 'agreements': 0, 'errors': 0}

# Sample data for testing - you can expand this
properties_data = [
    {'name': 'Jawhara Appartment', 'code': 'JAWHARA_AP', 'property_type': 'apartment', 'address': 'Jawhara Appartment, Deira, Dubai'},
    {'name': 'ADCB', 'code': 'ADCB', 'property_type': 'apartment', 'address': 'ADCB, Deira, Dubai'},
]

# 1. Import Properties
print("📦 Importing Properties...")
properties_map = {}

try:
    for prop_data in properties_data:
        try:
            existing = env['property.property'].search([('name', '=', prop_data['name'])], limit=1)
            if existing:
                print(f"   ⚠️  Property already exists: {prop_data['name']}")
                properties_map[prop_data['name']] = existing
            else:
                prop = env['property.property'].create(prop_data)
                properties_map[prop_data['name']] = prop
                stats['properties'] += 1
                print(f"   ✅ Created property: {prop_data['name']}")
        except Exception as e:
            print(f"   ❌ Error creating property {prop_data['name']}: {str(e)}")
            stats['errors'] += 1
            env.cr.rollback()
            continue
    
    env.cr.commit()
    print(f"\n✅ Properties section completed: {stats['properties']} created")
    
except Exception as e:
    print(f"\n❌ Fatal error in properties section: {str(e)}")
    env.cr.rollback()
    exit(1)

# 2. Import Flats
print("\n🏢 Importing Flats...")
flats_map = {}

# Sample flat data
flats_data = [
    {'property_name': 'Jawhara Appartment', 'flat_number': '102', 'floor': 1, 'flat_type': '2bhk'},
    {'property_name': 'Jawhara Appartment', 'flat_number': '201', 'floor': 2, 'flat_type': '2bhk'},
    {'property_name': 'ADCB', 'flat_number': '105', 'floor': 1, 'flat_type': '2bhk'},
]

try:
    for flat_data in flats_data:
        try:
            prop = properties_map.get(flat_data['property_name'])
            if not prop:
                print(f"   ⚠️  Property not found for flat: {flat_data['flat_number']}")
                continue
            
            existing = env['property.flat'].search([
                ('property_id', '=', prop.id),
                ('flat_number', '=', flat_data['flat_number'])
            ], limit=1)
            
            if existing:
                flats_map[f"{flat_data['property_name']}_{flat_data['flat_number']}"] = existing
                print(f"   ⚠️  Flat already exists: {flat_data['flat_number']}")
            else:
                flat = env['property.flat'].create({
                    'property_id': prop.id,
                    'flat_number': flat_data['flat_number'],
                    'floor': flat_data['floor'],
                    'flat_type': flat_data['flat_type'],
                })
                flats_map[f"{flat_data['property_name']}_{flat_data['flat_number']}"] = flat
                stats['flats'] += 1
                print(f"   ✅ Created flat: {flat_data['flat_number']} (Floor {flat_data['floor']}) in {flat_data['property_name']}")
        except Exception as e:
            print(f"   ❌ Error creating flat {flat_data.get('flat_number', 'Unknown')}: {str(e)}")
            stats['errors'] += 1
            env.cr.rollback()
            continue
    
    env.cr.commit()
    print(f"\n✅ Flats section completed: {stats['flats']} created")
    
except Exception as e:
    print(f"\n❌ Fatal error in flats section: {str(e)}")
    env.cr.rollback()
    exit(1)

# Print final statistics
print("\n" + "="*80)
print("Import Test Completed!")
print("="*80)
print(f"\n📊 Statistics:")
print(f"   Properties created: {stats['properties']}")
print(f"   Flats created: {stats['flats']}")
print(f"   Errors encountered: {stats['errors']}")
print("\n✅ Test import successful! Now you can run the full import.\n")
