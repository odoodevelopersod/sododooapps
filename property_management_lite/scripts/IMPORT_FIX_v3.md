# Import Fix v3 - Room Type Code Field

## Issue
The import was failing with error:
```
psycopg2.errors.NotNullViolation: null value in column "code" of relation "property_room_type" violates not-null constraint
```

## Root Cause
The `property.room.type` model requires a `code` field (unique identifier) that we weren't providing.

## Fix Applied
Updated the import script to include proper room type codes:
- `'single'` → Code: `'SINGLE'`
- `'attached'` → Code: `'ATTACH'`
- `'shared'` → Code: `'SHARED'`

## Progress So Far
✅ Properties: Successfully created (10 properties)
✅ Flats: Successfully created (227 flats with floor numbers)
⏳ Room Types: Fixed - now includes required code field
⏳ Rooms: Pending (954 rooms)
⏳ Tenants: Pending (752 tenants)
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
🚪 Ensuring Room Types exist...
   ✅ Created room type: single
   ✅ Created room type: attached
   ✅ Created room type: shared

🛏️  Importing Rooms...
   ✅ Created room: 102_1ST_SHARIN in flat 102
   ...
```

## What's Next
After room types are created successfully, the script will continue to:
1. Create 954 rooms
2. Create 752 tenants
3. Create 951 rental agreements
4. Activate all agreements

This should complete the full import!
