# Quick Fix Applied

## Issue
The import was failing with error:
```
ValueError: Wrong value for property.property.property_type: 'building'
```

## Root Cause
The property type was set to `'building'` but the valid values in the model are:
- `'apartment'` - Apartment Building
- `'villa'` - Villa
- `'office'` - Office Building
- `'warehouse'` - Warehouse
- `'commercial'` - Commercial Building

## Fix Applied
Changed the property type from `'building'` to `'apartment'` in the import script.

## Action Required
The import script has been regenerated. Please run it again:

```bash
# In Odoo shell:
>>> exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

The import should now work correctly!
