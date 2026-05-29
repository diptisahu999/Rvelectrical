# -*- coding: utf-8 -*-
from odoo import models, fields, api

class YesBankLog(models.Model):
    _name = 'yes.bank.log'
    _description = 'YES Bank Integration Logs'
    _order = 'create_date desc'

    name = fields.Char(string='Description')
    amount = fields.Float(string='Amount')
    payment_type = fields.Selection([
        ('incoming', 'Incoming (Client)'),
        ('outgoing', 'Outgoing (Vendor)')
    ], string='Payment Type', compute='_compute_payment_type', store=True)
    raw_data = fields.Text(string='Raw Data')
    status = fields.Selection([
        ('received', 'Received'),
        ('processed', 'Processed'),
        ('error', 'Error')
    ], string='Status', default='received')
    processed_date = fields.Datetime(string='Processed Date')

    @api.depends('amount')
    def _compute_payment_type(self):
        for rec in self:
            if rec.amount >= 0:
                rec.payment_type = 'incoming'
            else:
                rec.payment_type = 'outgoing'

    @api.model
    def get_query(self, domain, operation, measured_field_id, start_date=None, end_date=None, group_by=None):
        """Standard method for odoo_dynamic_dashboard compatibility"""
        model_name = self._table
        query = f"SELECT {operation}({measured_field_id.name}) as value FROM {model_name}"
        where_clauses = []
        if domain:
            # Simplified domain handling for this demonstration
            # In real scenario, would use self._where_calc(domain)
            pass
        if start_date:
            where_clauses.append(f"create_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"create_date <= '{end_date}'")
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        if group_by:
            query += f" GROUP BY {group_by.name}"
            
        return query
