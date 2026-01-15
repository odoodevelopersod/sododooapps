# Property Management Data Import Guide

## Overview
This guide explains how to import your existing property data from Excel files into the Odoo Property Management system.

## Data Summary
The import script has processed your Excel files and found:
- **10 Properties** (Buildings: ADCB, DEEMA, YAHYA, B.D, S.P, AL BAKER, AL DAR, JS, Jawhara Appartment, Jawhara METRO)
- **227 Flats** across all properties
- **954 Rooms** with various types (attached, shared, single)
- **752 Tenants** with active agreements
- **951 Rental Agreements** ready to be imported

## Import Steps

### Step 1: Prepare Your Odoo Environment
Make sure your Odoo instance is running and you have access to the database.

### Step 2: Run the Import Script

#### Option A: Using Odoo Shell (Recommended)
```bash
# Navigate to your Odoo installation directory
cd /path/to/odoo

# Start Odoo shell
./odoo-bin shell -d your_database_name -c /path/to/your_config.conf

# In the Odoo shell, run:
>>> exec(open('/path/to/property_management_lite/scripts/odoo_import_data.py').read())
```

#### Option B: Using Odoo Web Interface
1. Install the module if not already installed
2. Go to Settings → Technical → Automation → Scheduled Actions
3. Create a new scheduled action with the import script content
4. Run it manually

### Step 3: Verify the Import
After running the import script, you should see output like:
```
================================================================================
Starting Property Management Data Import
================================================================================

📦 Importing Properties...
   ✅ Created property: ADCB
   ✅ Created property: DEEMA
   ...

🏢 Importing Flats...
   ✅ Created flat: 105 in ADCB
   ...

🚪 Ensuring Room Types exist...
   ✅ Created room type: attached
   ...

🛏️  Importing Rooms...
   ✅ Created room: 105_ATTACH_BAL in flat 105
   ...

👤 Importing Tenants...
   ✅ Created tenant: GANESAN
   ...

📄 Importing Agreements...
   ✅ Created agreement: GANESAN - ADCB-105-105_ATTACH_BAL
   ...

================================================================================
Import Completed Successfully!
================================================================================

📊 Final Statistics:
   Properties created: 10
   Flats created: 227
   Rooms created: 954
   Tenants created: 752
   Agreements created: 951

✅ All data imported successfully!
```

### Step 4: Check Your Data
1. Go to Property Management → Properties
2. Verify all properties are listed
3. Check flats and rooms for each property
4. Go to Tenant Management → Tenants
5. Verify tenant information
6. Go to Tenant Management → Agreements
7. Verify all agreements are active

## Important Notes

### Data Mapping
- **Room Types**: Automatically normalized to: `attached`, `shared`, or `single`
- **Agreement Dates**: Default start date is August 1, 2025, end date is July 31, 2026
- **Status**: All agreements are created as `draft` first, then activated automatically
- **Deposits**: Special formats like "(1000-500)" are calculated as 500

### Duplicate Handling
The script checks for existing records and will:
- Skip creating duplicates for properties, flats, and tenants
- Show warnings for existing records
- Only create new records when they don't exist

### Room Numbering
Rooms are numbered using the format: `{flat_number}_{room_type_abbreviation}`
Example: `105_ATTACH_BAL` for an attached room with balcony in flat 105

## Troubleshooting

### Issue: "Property not found for flat"
**Solution**: Make sure properties are created first. The script creates them in order.

### Issue: "Tenant not found"
**Solution**: Check if tenant names match exactly. The script is case-sensitive.

### Issue: "Agreement already exists"
**Solution**: This is normal if you're re-running the import. Existing agreements won't be duplicated.

### Issue: Import fails midway
**Solution**: The script commits after each section (properties, flats, rooms, tenants, agreements). You can safely re-run it, and it will skip already imported records.

## Re-running the Import
If you need to re-run the import:
1. The script is safe to run multiple times
2. It will skip existing records
3. Only new records will be created
4. Check the output for warnings about existing records

## Support
If you encounter any issues:
1. Check the Odoo logs for detailed error messages
2. Verify your database connection
3. Ensure all required modules are installed
4. Check that you have proper permissions

## Next Steps After Import
1. Review all imported data
2. Update any missing information (phone numbers, emails, etc.)
3. Set up payment schedules
4. Configure invoice generation settings
5. Start collecting rent and managing properties!
