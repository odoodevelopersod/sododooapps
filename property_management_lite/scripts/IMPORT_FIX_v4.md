# Import Fix v4 - Tenant Required Fields

## Issue
The import was failing with error:
```
psycopg2.errors.NotNullViolation: null value in column "mobile" of relation "property_tenant" violates not-null constraint
```

## Root Cause
The `property.tenant` model requires several fields that we weren't providing:
- `mobile` (required)
- `phone` (required)
- `email` (required)
- `id_passport` (required)

## Fix Applied
Updated the import script to generate placeholder values for missing tenant information:

```python
# For tenant "ABDUL WAHID":
mobile: '0507654321'  # Generated from name hash
phone: '0507654321'   # Same as mobile
email: 'abdul.wahid@placeholder.com'  # Generated from name
id_passport: 'ID7654321'  # Generated ID number
```

## Progress So Far
✅ Properties: Successfully created (10 properties)
✅ Flats: Successfully created (227 flats)
✅ Room Types: Successfully created (3 types: single, attached, shared)
✅ Rooms: Successfully created (954 rooms)
⏳ Tenants: Fixed - now includes required fields
⏳ Agreements: Pending (951 agreements)

## Action Required
Rollback the failed transaction and run the import again:

```python
# In Odoo shell:
env.cr.rollback()
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

Or use the one-liner:
```python
env.cr.rollback(); exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

## Expected Output
After the fix, you should see:
```
👤 Importing Tenants...
   ✅ Created tenant: ABDUL WAHID
   ✅ Created tenant: AYUB
   ✅ Created tenant: FIRAS
   ...

📄 Importing Agreements...
   ✅ Created agreement: ABDUL WAHID - Jawhara Appartment-102-102_1ST_SHARIN
   ...
```

## Important Note
The placeholder contact information (mobile, email, ID) should be updated with real data after import:
1. Go to Tenant Management → Tenants
2. Edit each tenant
3. Update mobile, email, and ID/passport with actual information

## What's Next
After tenants are created successfully, the script will:
1. Create 951 rental agreements
2. Activate all agreements automatically
3. Complete the full import!

This is the final step!
