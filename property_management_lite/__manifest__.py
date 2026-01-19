{
    'name': 'Property Management Lite',
    'version': '18.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Complete Property & Room Rental Management System with Advanced Financial Tracking',
    'description': """
Property Management Lite - Complete Solution
============================================

A comprehensive property and room rental management system featuring:

**Property Structure Management:**
* Multi-level Property → Flat → Room hierarchy
* Room type classification and availability tracking
* Comprehensive property details and documentation

**Tenant & Agreement Management:**
* Complete tenant profiles with documents and emergency contacts
* Flexible rental agreements with automatic calculations
* Multi-tenant room support and tenant history tracking

**Financial Management:**
* Daily rent collection with multiple payment methods
* Other charges system (parking, utilities, maintenance)
* Outstanding dues tracking with automated calculations
* Statement of account with complete transaction history
* Collection efficiency analysis and overdue management

**Advanced Features:**
* Real-time dashboard with financial KPIs
* Automated rent period calculations (monthly cycles)
* Color-coded tenant status and payment tracking
* Comprehensive reporting and analytics
* Agent management and performance tracking

**Designed for:**
* Property management companies
* Real estate agents
* Building owners and landlords
* Multi-property portfolios

Optimized for Dubai real estate market with AED currency support.
    """,
    'author': 'SOD Infotech',
    'website': 'https://sodinfotech.com/',
    'license': 'OPL-1',
    'price': 110.00,
    'category': 'Real Estate',
    'depends': [
        'base',
        'contacts',
        'mail',
        'web',
        'sale',
        'account',
    ],
    'data': [
        # Security
        'security/property_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/property_data.xml',
        'data/sequences.xml',
        'data/product.xml',
        'data/agent_data.xml',
        'data/scheduled_actions.xml',
        'data/cron_recompute_outstanding_dues.xml',
        'data/cron_update_outstanding_dues.xml',
        'data/cron_generate_statement_entries.xml',
        'data/cron_create_collection_statements.xml',
        'data/cron_cleanup_statement_entries.xml',
        'data/cron_recalculate_balances.xml',
        # 'data/email_templates.xml',

        # Views - Dashboard
        'views/dashboard_views.xml',
        
        # Views
        # 'views/menu_views.xml',
        'views/property_views.xml',
        'views/flat_views.xml',
        'views/room_views.xml',
        'views/room_type_views.xml',
        'views/agreement_views.xml',
        'views/collection_views.xml',
        'views/statement_views.xml',
        'views/outstanding_dues_views.xml',
        'views/occupant_views.xml',
        'views/other_charges_views.xml',
        'views/agent_views.xml',
        'views/agreement_clean_wizard_views.xml',
        'views/tenant_views.xml',

        # Wizards
        'wizards/property_data_import_wizard_views.xml',
        'views/statement_wizard_views.xml',  # Fixed path
        
        # Report templates
        'reports/invoice_reports.xml',
        
        # Email Templates (must come before views that reference them)
        'data/email_templates.xml',
        'views/invoice_views.xml',


        # Invoice views (references email templates)
        'views/invoice_views.xml',
        # Menus (must come after all views that define actions)
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
