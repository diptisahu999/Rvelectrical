from odoo import http
from odoo.http import request
import json

class DashboardTodayController(http.Controller):
    
    @http.route('/dashboard/today/data', type='json', auth='user')
    def get_today_data(self):
        """API endpoint for today's dashboard data"""
        dashboard_model = request.env['dashboard.today']
        return dashboard_model.get_today_sales_data()
    
    @http.route('/dashboard/today/chart', type='json', auth='user')
    def get_today_chart_data(self):
        """API endpoint for today's chart data"""
        dashboard_model = request.env['dashboard.today']
        return dashboard_model.get_today_chart_data()