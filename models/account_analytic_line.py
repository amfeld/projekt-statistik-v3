from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to trigger project analytics recomputation when timesheets are created.
        """
        lines = super().create(vals_list)
        self._trigger_project_analytics_recompute(lines)
        return lines

    def write(self, vals):
        """
        Override write to trigger project analytics recomputation when timesheets are modified.
        Only triggers when relevant fields change.
        """
        result = super().write(vals)

        # Only trigger recompute if fields that affect project analytics changed
        if any(key in vals for key in ['account_id', 'unit_amount', 'amount', 'employee_id', 'is_timesheet']):
            self._trigger_project_analytics_recompute(self)

        return result

    def unlink(self):
        """
        Override unlink to trigger project analytics recomputation when timesheets are deleted.
        """
        # Trigger BEFORE deletion so we can still access the data
        self._trigger_project_analytics_recompute(self)
        return super().unlink()

    def _trigger_project_analytics_recompute(self, lines):
        """
        Trigger recomputation of project analytics when analytic lines (timesheets) change.

        Optimizations:
        - Batch processing
        - Error handling per batch
        - Deduplication of project IDs

        Args:
            lines: Recordset of account.analytic.line records that changed
        """
        if not lines:
            return

        project_ids = set()

        try:
            # Get project plan reference once
            try:
                project_plan = self.env.ref('analytic.analytic_plan_projects', raise_if_not_found=False)
            except Exception as e:
                _logger.warning(f"Could not load project plan reference: {e}")
                return

            if not project_plan:
                _logger.debug("Project analytic plan not found - skipping recompute trigger")
                return

            # Collect all unique analytic account IDs
            analytic_account_ids = set()
            for line in lines:
                if line.account_id:
                    analytic_account_ids.add(line.account_id.id)

            if not analytic_account_ids:
                return

            # Batch-fetch all analytic accounts
            analytic_accounts = self.env['account.analytic.account'].browse(list(analytic_account_ids))

            # Filter for project plan accounts only
            project_analytic_accounts = analytic_accounts.filtered(
                lambda a: a.exists() and a.plan_id == project_plan
            )

            if not project_analytic_accounts:
                return

            # Find all projects linked to these analytic accounts in one query
            projects = self.env['project.project'].search([
                '|',
                ('analytic_account_id', 'in', project_analytic_accounts.ids),
                ('account_id', 'in', project_analytic_accounts.ids)
            ])

            if not projects:
                return

            project_ids = set(projects.ids)

        except Exception as e:
            _logger.error(f"Error collecting projects for analytics recompute (analytic lines): {e}", exc_info=True)
            return

        # Batch process projects
        if project_ids:
            project_ids_list = list(project_ids)
            chunk_size = 50
            total_projects = len(project_ids_list)

            _logger.info(f"Triggering recompute for {total_projects} project(s) after analytic line change")

            for i in range(0, total_projects, chunk_size):
                chunk = project_ids_list[i:i + chunk_size]
                chunk_projects = self.env['project.project'].browse(chunk)

                try:
                    # Recompute financial data for this batch
                    chunk_projects._compute_financial_data()

                    # Commit after each batch
                    if not self.env.context.get('defer_commit'):
                        self.env.cr.commit()

                    _logger.info(f"Recomputed financial data for {len(chunk_projects)} project(s) (analytic lines)")

                except Exception as e:
                    _logger.error(
                        f"Error recomputing financial data for projects {chunk}: {e}",
                        exc_info=True
                    )
                    if not self.env.context.get('defer_commit'):
                        self.env.cr.rollback()
                    continue
