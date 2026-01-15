# Import Fix v7 - Duplicate Room Assignments

## Issue
The import was failing with error:
```
ValidationError: Room is already rented during this period! Conflicting agreement: AGR/OSAMA/JAWHARA_AP-FEMALE GYM-FEMALE GYM_MAID_ROOM_/20250801 (from 2025-08-01 to 2026-07-31)
```

## Root Cause
The source Excel data contains duplicate room assignments - the same room is assigned to multiple tenants with overlapping dates. This is a data quality issue in the original Excel files.

For example:
- Room "FEMALE GYM_MAID_ROOM_" has multiple tenants assigned
- All with the same date range (2025-08-01 to 2026-07-31)
- This violates the business rule: one room can only have one active tenant at a time

## Fix Applied
Updated the import script to handle duplicate room assignments gracefully:

```python
# Check if room is already occupied by another tenant
room_occupied = env['property.agreement'].search([
    ('room_id', '=', room.id),
    ('state', '=', 'active')
], limit=1)

if room_occupied:
    print(f"⚠️  Room {room.name} is already occupied by {room_occupied.tenant_id.name}, skipping {tenant.name}")
    continue
```

## What This Means
- **First tenant** for each room will get the agreement created
- **Subsequent tenants** for the same room will be skipped with a warning
- The import will continue without errors
- You'll see warnings for skipped agreements

## Action Required
Run the import again:

```python
# In Odoo shell:
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

## Expected Output
```
📄 Importing Agreements...
   ✅ Created agreement: OSAMA - JAWHARA_AP-FEMALE GYM-FEMALE GYM_MAID_ROOM_
   ⚠️  Room FEMALE GYM_MAID_ROOM_ is already occupied by OSAMA, skipping ANOTHER_TENANT
   ✅ Created agreement: ABDUL WAHID - Jawhara Appartment-102-102_1ST_SHARIN
   ...

================================================================================
Import Completed Successfully!
================================================================================

📊 Final Statistics:
   Properties created: 0
   Flats created: 0
   Rooms created: 0
   Tenants created: 0
   Agreements created: XXX (less than 951 due to duplicates)

✅ All data imported successfully!
```

## Post-Import Action Required

### Review Skipped Agreements
After import, you should:

1. **Check the import log** for warnings about skipped tenants
2. **Review duplicate room assignments** in your Excel data
3. **Decide which tenant should occupy each room**
4. **Manually create agreements** for the correct tenants if needed

### Common Scenarios for Duplicates
- **Shared rooms**: Multiple tenants in one room (need to create separate bed spaces)
- **Data entry errors**: Same room listed twice by mistake
- **Tenant changes**: Old tenant data not removed when new tenant moved in

### How to Fix Duplicates
1. Go to Property Management → Agreements
2. Find agreements for rooms with multiple tenants
3. Either:
   - Terminate incorrect agreements
   - Create separate room partitions for shared rooms
   - Update room assignments

## Summary
The import will now complete successfully, skipping duplicate room assignments. You'll need to manually review and fix the duplicate data after import.
