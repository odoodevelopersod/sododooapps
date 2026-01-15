# Import Fix v2 - Floor Field Required

## Issue
The import was failing with error:
```
psycopg2.errors.NotNullViolation: null value in column "floor" of relation "property_flat" violates not-null constraint
```

## Root Cause
The `property.flat` model requires two fields that we weren't providing:
- `floor` (Integer, required) - The floor number where the flat is located
- `flat_type` (Selection, required) - The type of flat (studio, 1bhk, 2bhk, etc.)

## Fix Applied
Updated the import script to:
1. **Extract floor number** from flat number automatically:
   - Flat 102 → Floor 1
   - Flat 305 → Floor 3
   - Flat 1001 → Floor 10
   - Non-numeric flats (like "M01", "MALE GYM") → Floor 0 (Ground)

2. **Set default flat type** to '2bhk' (can be updated manually later)

## Floor Extraction Logic
```python
# For flat number "305":
floor_num = int("305"[:-2])  # = 3

# For flat number "102":
floor_num = int("102"[0])  # = 1

# For flat number "M01":
floor_num = 0  # Ground floor
```

## Action Required
The import script has been regenerated with these fixes. Please run it again:

```python
# In Odoo shell:
exec(open('Custom_Addons/property_management_lite/scripts/odoo_import_data.py').read())
```

## Expected Output
You should now see:
```
✅ Created flat: 102 (Floor 1) in Jawhara Appartment
✅ Created flat: 305 (Floor 3) in Jawhara Appartment
...
```

## Note
After import, you may want to:
1. Review and update flat types (studio, 1bhk, 2bhk, 3bhk, etc.)
2. Verify floor numbers are correct
3. Update any special cases (gym, parking areas, etc.)
