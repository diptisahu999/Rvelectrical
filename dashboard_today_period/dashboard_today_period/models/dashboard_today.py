from odoo import models, fields, api
from datetime import datetime, date
import json

class DashboardToday(models.Model):
    _name = 'dashboard.today'
    _description = 'Dashboard Today Period'

    @api.model
    def get_today_sales_data(self):
        """Get today's sales data"""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Get today's sales orders
        sales_today = self.env['sale.order'].search([
            ('date_order', '>=', today_start),
            ('date_order', '<=', today_end),
            ('state', 'in', ['sale', 'done'])
        ])
        
        # Get today's invoices
        invoices_today = self.env['account.move'].search([
            ('invoice_date', '=', today),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ])
        
        # Calculate totals
        total_sales = sum(sales_today.mapped('amount_total'))
        total_invoices = len(invoices_today)
        total_invoice_amount = sum(invoices_today.mapped('amount_total'))
        
        # Get average invoice amount
        avg_invoice = total_invoice_amount / total_invoices if total_invoices > 0 else 0
        
        # Get top invoices for today
        top_invoices = invoices_today.sorted(key=lambda x: x.amount_total, reverse=True)[:5]
        
        invoice_data = []
        for invoice in top_invoices:
            invoice_data.append({
                'reference': invoice.name,
                'salesperson': invoice.user_id.name or 'N/A',
                'status': invoice.payment_state.title() if invoice.payment_state else 'Draft',
                'customer': invoice.partner_id.name,
                'date': invoice.invoice_date.strftime('%m/%d/%Y') if invoice.invoice_date else '',
                'amount': invoice.amount_total
            })
        
        return {
            'invoiced': int(total_invoice_amount),
            'average_invoice': int(avg_invoice),
            'total_invoices': total_invoices,
            'unpaid_count': len(invoices_today.filtered(lambda x: x.payment_state == 'not_paid')),
            'top_invoices': invoice_data,
            'sales_count': len(sales_today),
            'total_sales': total_sales,
        }
    
    @api.model
    def get_today_chart_data(self):
        """Get chart data for today (hourly breakdown)"""
        today = date.today()
        
        # Get hourly sales data for today
        hourly_data = []
        for hour in range(24):
            hour_start = datetime.combine(today, datetime.min.time().replace(hour=hour))
            hour_end = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=59, second=59))
            
            sales_hour = self.env['sale.order'].search([
                ('date_order', '>=', hour_start),
                ('date_order', '<=', hour_end),
                ('state', 'in', ['sale', 'done'])
            ])
            
            hourly_total = sum(sales_hour.mapped('amount_total'))
            if hourly_total > 0:  # Only include hours with sales
                hourly_data.append({
                    'hour': f"{hour:02d}:00",
                    'amount': hourly_total
                })
        
        return hourly_data

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def get_period_data(self, period):
        """Override to handle 'today' period"""
        if period == 'today':
            return self.env['dashboard.today'].get_today_sales_data()
        return super().get_period_data(period)