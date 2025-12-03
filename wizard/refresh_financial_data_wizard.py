from odoo import models, fields, api, _


class RefreshFinancialDataWizard(models.TransientModel):
    _name = 'refresh.financial.data.wizard'
    _description = 'Refresh Financial Data with General Hourly Rate'

    general_hourly_rate = fields.Float(
        string='General Hourly Rate (EUR)',
        required=True,
        default=lambda self: float(
            self.env['ir.config_parameter'].sudo().get_param(
                'project_statistic.general_hourly_rate', default='66.0'
            )
        ),
        help="General hourly rate used to calculate adjusted labor costs. "
             "Formula: Total Hours Booked (Adjusted) × General Hourly Rate = Labor Costs (Adjusted)"
    )

    def action_refresh_data(self):
        """
        Update the system parameter with the new hourly rate and refresh financial data.
        """
        self.ensure_one()

        # Update the system parameter
        self.env['ir.config_parameter'].sudo().set_param(
            'project_statistic.general_hourly_rate',
            str(self.general_hourly_rate)
        )

        # Get the active project IDs from context
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            projects = self.env['project.project'].browse(active_ids)
        else:
            # If no specific projects selected, refresh all
            projects = self.env['project.project'].search([])

        # Trigger recomputation
        projects._compute_financial_data()

        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Financial Data Refreshed'),
                'message': _('Financial data has been recalculated for %s project(s) with hourly rate %.2f EUR.') % (
                    len(projects), self.general_hourly_rate
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
