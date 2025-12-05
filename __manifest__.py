{
    'name': 'Project Statistic',
    'version': '18.0.1.0.16',
    'category': 'Project',
    'summary': 'Enhanced project analytics with financial data',
    'description': """
        Project Analytics Module
        ========================
        Provides comprehensive financial analytics for projects including:
        - Customer invoicing and payment tracking
        - Vendor bill management
        - Cost analysis with tax calculations
        - Profit/loss calculations
        - Labor cost tracking from timesheets
    """,
    'depends': [
        'project',
        'account',
        'accountant',  # Odoo 18 Enterprise accounting features
        'analytic',
        'hr_timesheet',
        'timesheet_grid',  # Odoo 18 Enterprise timesheet grid
        'sale',
        'sale_project',  # Required for project_id field on sale.order
    ],
    'author': 'Alex Feld',
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'wizard/refresh_financial_data_wizard_views.xml',
        'views/hr_employee_views.xml',
        'views/project_analytics_views.xml',  # Must be loaded before menuitem.xml (defines actions)
        'data/menuitem.xml',  # Loaded last (references actions from views)
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
}