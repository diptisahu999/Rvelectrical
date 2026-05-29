from odoo import models, fields, api, tools
from datetime import date


class DashboardTeamPerformance(models.Model):
    _name = 'dashboard.team.performance'
    _description = 'Dashboard Team Performance'
    _auto = False   # IMPORTANT (SQL-based model)

    user_id = fields.Many2one('res.users', string='User')
    target = fields.Float(string='Target')
    leads_created = fields.Integer(string='Leads Created')
    opportunities_created = fields.Integer(string='Opportunities Created')
    sales_revenue = fields.Float(string='Sales Revenue')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'dashboard_team_performance')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW dashboard_team_performance AS (
                SELECT
                    row_number() OVER () AS id,
                    u.id AS user_id,
                    COALESCE(SUM(stl.target_amount), 0) AS target,
                    COALESCE(l.leads, 0) AS leads_created,
                    COALESCE(o.opps, 0) AS opportunities_created,
                    COALESCE(s.revenue, 0) AS sales_revenue
                FROM res_users u
                LEFT JOIN sales_target st ON st.user_id = u.id
                LEFT JOIN sales_target_line stl ON stl.target_id = st.id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) AS leads
                    FROM crm_lead
                    WHERE type = 'lead'
                    GROUP BY user_id
                ) l ON l.user_id = u.id
                LEFT JOIN (
                    SELECT user_id, COUNT(*) AS opps
                    FROM crm_lead
                    WHERE type = 'opportunity'
                    GROUP BY user_id
                ) o ON o.user_id = u.id
                LEFT JOIN (
                    SELECT user_id, SUM(amount_total) AS revenue
                    FROM sale_order
                    WHERE state IN ('sale','done')
                    GROUP BY user_id
                ) s ON s.user_id = u.id
                GROUP BY u.id, l.leads, o.opps, s.revenue
            )
        """)
