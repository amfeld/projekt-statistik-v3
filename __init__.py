from . import models
from . import wizard


def uninstall_hook(env):
    """
    Clean up stored computed fields when module is uninstalled.

    Note: This hook runs AFTER module uninstallation, so we must be careful
    not to break Odoo's own cleanup process. We only remove fields that Odoo
    might not clean up automatically (stored computed fields).

    DO NOT manually commit here - let Odoo handle the transaction.
    """
    import logging
    _logger = logging.getLogger(__name__)

    _logger.info("Running project_statistic uninstall hook")

    # List of custom fields to remove from project.project
    fields_to_remove = [
        # Currency field
        'currency_id',

        # Status fields
        'has_analytic_account',
        'data_availability_status',

        # Sales Order fields
        'sale_order_amount_net',
        'manual_sales_order_amount_net',
        'sale_order_tax_names',

        # Customer Invoice NET fields
        'customer_invoiced_amount_net',
        'customer_paid_amount_net',
        'customer_outstanding_amount_net',

        # Customer Invoice GROSS fields
        'customer_invoiced_amount_gross',
        'customer_paid_amount_gross',
        'customer_outstanding_amount_gross',

        # Vendor Bills NET/GROSS fields
        'vendor_bills_total_net',
        'vendor_bills_total_gross',

        # Skonto fields
        'customer_skonto_taken',
        'vendor_skonto_received',

        # Labor fields
        'total_hours_booked',
        'labor_costs',
        'total_hours_booked_adjusted',
        'labor_costs_adjusted',

        # Other cost fields
        'other_costs_net',

        # Total cost fields
        'total_costs_net',

        # Profitability fields
        'profit_loss_net',
        'negative_difference_net',

        # Basic info fields
        'client_name',
        'head_of_project',
        'sequence'
    ]

    # First, try to remove ir.model.fields records (clean ORM way)
    try:
        IrModelFields = env['ir.model.fields'].sudo()
        ProjectModel = env['ir.model'].sudo().search([('model', '=', 'project.project')], limit=1)

        if ProjectModel:
            for field_name in fields_to_remove:
                field_record = IrModelFields.search([
                    ('model_id', '=', ProjectModel.id),
                    ('name', '=', field_name),
                    ('state', '=', 'manual')  # Only remove manually created fields
                ], limit=1)

                if field_record:
                    try:
                        field_record.unlink()
                        _logger.info(f"Removed field '{field_name}' from project.project")
                    except Exception as e:
                        _logger.warning(f"Could not remove field '{field_name}': {e}")

        _logger.info("Field cleanup completed")

    except Exception as e:
        _logger.warning(f"Error during field cleanup: {e}")

    # Second, drop database columns as fallback (only if ORM cleanup failed)
    # This is more aggressive and should only run if fields still exist
    try:
        from psycopg2 import sql

        # Check which columns actually exist before trying to drop them
        env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'project_project'
            AND column_name = ANY(%s)
        """, (fields_to_remove,))

        existing_columns = [row[0] for row in env.cr.fetchall()]

        if existing_columns:
            _logger.info(f"Found {len(existing_columns)} columns to drop: {existing_columns}")

            for field in existing_columns:
                try:
                    query = sql.SQL("ALTER TABLE project_project DROP COLUMN IF EXISTS {} CASCADE").format(
                        sql.Identifier(field)
                    )
                    env.cr.execute(query)
                    _logger.info(f"Dropped column '{field}' from project_project")
                except Exception as field_error:
                    _logger.warning(f"Could not drop column {field}: {field_error}")
        else:
            _logger.info("No columns to drop (already cleaned up)")

    except Exception as e:
        _logger.warning(f"Error during database column cleanup: {e}")
        # Don't raise - we want uninstall to continue even if cleanup fails

    _logger.info("project_statistic uninstall hook completed")

    # DO NOT commit here - Odoo handles the transaction