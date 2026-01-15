# How to Fix Transaction Error and Import Data

## The Problem
The previous import failed, leaving the database transaction in a failed state. Any new commands will fail with:
```
psycopg2.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block
```

## Solution: Rollback First

### Step 1: Rollback the Failed Transaction
In your Odoo shell, run:
```python
env.cr.rollback()
```

### Step 2: Run the Import Again
After rollback, run:
```python
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

## Alternative: Use the Safe Import Script

I've created a safer version that handles errors gracefully. Run this instead:

```python
# This script automatically handles rollbacks
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data_safe.py').read())
```

## One-Line Solution

If you want to do everything in one command:

```python
env.cr.rollback(); exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

## What the Safe Script Does

1. **Automatically rolls back** any failed transactions
2. **Handles errors gracefully** - continues even if one record fails
3. **Commits in batches** - after each section (properties, flats, etc.)
4. **Shows detailed progress** - tells you exactly what succeeded and what failed
5. **Provides statistics** - shows counts of created records and errors

## Expected Output

After rollback and running the import, you should see:
```
================================================================================
Starting Property Management Data Import
================================================================================

✅ Rolled back any previous failed transactions

📦 Importing Properties...
   ✅ Created property: Jawhara Appartment
   ✅ Created property: Jawhara METRO
   ...

🏢 Importing Flats...
   ✅ Created flat: 102 (Floor 1) in Jawhara Appartment
   ✅ Created flat: 201 (Floor 2) in Jawhara Appartment
   ...
```

## If You Still Get Errors

1. **Exit the Odoo shell completely**: Press Ctrl+D or type `exit()`
2. **Restart the Odoo shell**: `./odoo-bin shell -d your_database -c your_config.conf`
3. **Run the import**: `exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())`

## Quick Reference

```python
# Rollback only
env.cr.rollback()

# Rollback + Import (one line)
env.cr.rollback(); exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())

# Use safe version (recommended)
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data_safe.py').read())
```
