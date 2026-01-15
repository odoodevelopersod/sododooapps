# -*- coding: utf-8 -*-
"""
Enable Auto-Post Invoices for Existing Agreements

Run this script from Odoo shell to enable auto-post for all existing agreements:
    odoo-bin shell -d your_database -c your_config.conf
    >>> exec(open('Custom_Addons/property_management_lite/scripts/enable_auto_post_invoices.py').read())
"""

# Get environment
env = globals().get('env')
if not env:
    print("ERROR: This script must be run from Odoo shell")
    print("Usage: odoo-bin shell -d your_database")
    print("Then: exec(open('Custom_Addons/property_management_lite/scripts/enable_auto_post_invoices.py').read())")
    exit(1)

print("\n" + "="*80)
print("Enabling Auto-Post Invoices for All Agreements")
print("="*80 + "\n")

# Find all agreements
agreements = env['property.agreement'].search([])

print(f"Found {len(agreements)} agreements")

# Update auto_post_invoices to True
updated = 0
for agreement in agreements:
    if not agreement.auto_post_invoices:
        agreement.write({'auto_post_invoices': True})
        updated += 1

env.cr.commit()

print(f"\n✅ Updated {updated} agreements to enable auto-post invoices")
print(f"✅ {len(agreements) - updated} agreements already had auto-post enabled")
print("\n" + "="*80)
print("Completed Successfully!")
print("="*80 + "\n")
print("From now on, all generated invoices will be automatically posted (confirmed).")
print()
