# pyrefly: ignore [missing-import]
from odoo import models, fields, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class DailyReport(models.TransientModel):
    _name = 'crm.daily.report'
    _description = 'CRM Daily Report'

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    @api.model
    def get_dashboard_data(self, filters=None):
        """ Fetch data for the OWL Dashboard with dynamic filters """
        if filters is None:
            filters = {}

        # 1. PREPARE DOMAINS
        # We need base domains for each major model that incorporate the filters
        dom_lead = [('type', '=', 'lead')] + self._get_filter_domain('crm.lead', filters)
        dom_opp = [('type', '=', 'opportunity')] + self._get_filter_domain('crm.lead', filters)
        dom_sale = [('state', 'in', ['sale', 'done'])] + self._get_filter_domain('sale.order', filters)
        dom_move = [('move_type', '=', 'out_invoice'), ('state', '!=', 'cancel')] + self._get_filter_domain('account.move', filters)
        dom_purchase = [('state', 'in', ['purchase', 'done'])] + self._get_filter_domain('purchase.order', filters)
        
        # 2. KPI CALCULATIONS
        
        # CRM
        leads_count = self.env['crm.lead'].search_count(dom_lead)
        opps_count = self.env['crm.lead'].search_count(dom_opp)
        
        pipeline = self.env['crm.lead'].search(dom_opp + [('stage_id.is_won', '=', False)])
        pipeline_val = sum(pipeline.mapped('expected_revenue'))
        
        won_count = self.env['crm.lead'].search_count(dom_opp + [('stage_id.is_won', '=', True)])
        lost_count = self.env['crm.lead'].search_count(dom_opp + [('active', '=', False)]) # Note: _get_filter_domain handles active=False case? 
        # Standard search excludes active=False. We need to handle Lost specifically if we want them.
        # But usually filters apply to active records. Lost are inactive.
        # For conversion rate, we might need lost.
        # Let's simplify conversion: Won / (Won + Open) or just Won / Count.
        
        conversion = (won_count / opps_count * 100) if opps_count else 0
        
        # SALES
        orders = self.env['sale.order'].search(dom_sale)
        revenue = sum(orders.mapped('amount_total'))
        avg_order = revenue / len(orders) if orders else 0
        
        confirmed_orders_count = self.env['sale.order'].search_count(dom_sale + [('invoice_status', '=', 'to invoice'), ('picking_ids.state', 'not in', ['done', 'cancel'])])
        
        # INVOICES
        invoices_count = self.env['account.move'].search_count(dom_move)
        
        # EXTRA METRICS
        # Note: Stock usually doesn't filter by Partner/City, but does by Product/Category.
        # We pass filters to sub-methods.
        
        return {
            'kpis': {
                'leads_count': leads_count,
                'opportunities_count': opps_count,
                'pipeline_value': pipeline_val,
                'lead_conversion': round(conversion, 1),
                'confirmed_orders': confirmed_orders_count,
                'sales_revenue': revenue,
                'avg_order_value': round(avg_order, 2),
                'invoices': invoices_count,
                
                'purchase_total': self._get_purchase_total(filters),
                'stock_value': self._get_stock_value(filters),
                'payment_in': self._get_payment_in(filters),
                'advance_given': self._get_advance_given(filters),
                'advance_received': self._get_advance_received(filters),
                'yes_bank_incoming': self._get_yes_bank_incoming(filters),
                'yes_bank_outgoing': self._get_yes_bank_outgoing(filters),
                'yes_bank_balance': self._get_yes_bank_balance(filters),
            },
            'team_performance': self._get_team_performance(filters),
            'recent_orders': self._get_recent_orders(filters),
            'top_deals': self._get_top_deals(filters),
            'opportunity_dashboard': self._get_opportunity_dashboard_data(filters),
            'sales_dashboard': self._get_sales_dashboard_data(filters),
        }

    def _get_filter_domain(self, model, filters):
        """ Construct search domain based on filters and model """
        domain = []
        
        # 1. DATE RANGE
        # Identify date field per model
        date_field = 'create_date' # Default
        if model == 'sale.order': date_field = 'date_order'
        elif model == 'purchase.order': date_field = 'date_order'
        elif model == 'account.move': date_field = 'invoice_date'
        elif model == 'account.payment': date_field = 'date'
        elif model in ['stock.quant', 'product.product', 'rv.stock.overview']: date_field = None # Stock is usually "Current", no date filter unless partial history
        
        if date_field:
            if filters.get('date_from'):
                domain.append((date_field, '>=', filters['date_from']))
            if filters.get('date_to'):
                domain.append((date_field, '<=', filters['date_to']))

        # 2. COMMON FIELDS (User, Team, Company)
        if filters.get('user_id') and model in ['crm.lead', 'sale.order', 'purchase.order', 'account.move']:
            # Account move uses invoice_user_id for salesperson
            fld = 'invoice_user_id' if model == 'account.move' else 'user_id'
            domain.append((fld, '=', filters['user_id']))
            

        # 3. PARTNER FIELDS (Customer, Country, State, City)
        # Identify partner field
        partner_field = 'partner_id'
        if model in ['crm.lead', 'sale.order', 'purchase.order', 'account.move', 'account.payment']:
             if filters.get('partner_id'):
                 domain.append((partner_field, '=', filters['partner_id']))
                 


             # State (Requested)
             if filters.get('state_id'):
                 if model == 'crm.lead':
                     domain.append(('state_id', '=', filters['state_id']))
                 else:
                     domain.append((f'{partner_field}.state_id', '=', filters['state_id']))

             # City (Requested)
             if filters.get('city'):
                 if model == 'crm.lead':
                      domain.append(('city', 'ilike', filters['city']))
                 else:
                      domain.append((f'{partner_field}.city', 'ilike', filters['city']))
                      
             # Customer Name (Text Search)
             if filters.get('customer_name'):
                 if model == 'crm.lead':
                     domain.append(('partner_name', 'ilike', filters['customer_name'])) # Fallback or search partner_id.name
                 else:
                     domain.append((f'{partner_field}.name', 'ilike', filters['customer_name']))

        # 4. PRODUCT FIELDS (Product, Category)
        # Apply to: Sale, Purchase, Move, Stock
        # These models have lines. We search for header records that CONTAIN the product.
        if filters.get('product_name'):
            if model == 'sale.order':
                domain.append(('order_line.product_id.name', 'ilike', filters['product_name']))
            elif model == 'purchase.order':
                domain.append(('order_line.product_id.name', 'ilike', filters['product_name']))
            elif model == 'account.move':
                domain.append(('invoice_line_ids.product_id.name', 'ilike', filters['product_name']))
            elif model == 'stock.quant':
                domain.append(('product_id.name', 'ilike', filters['product_name']))
            elif model == 'product.product':
                domain.append(('name', 'ilike', filters['product_name']))
            elif model == 'rv.stock.overview':
                domain.append(('product_id.name', 'ilike', filters['product_name']))
                

        # 5. MARKETING (Source, Medium)
        if model in ['crm.lead', 'sale.order', 'account.move']:
            if filters.get('source_id'):
                domain.append(('source_id', '=', filters['source_id']))
            if filters.get('medium_id'):
                domain.append(('medium_id', '=', filters['medium_id']))
                
        return domain

    @api.model
    def get_context_domain(self, model, filters=None):
        if not filters:
            filters = {}
        return self._get_filter_domain(model, filters)

    def _get_purchase_total(self, filters):
        dom = [('state', 'in', ['purchase', 'done'])] + self._get_filter_domain('purchase.order', filters)
        purchases = self.env['purchase.order'].search(dom)
        return sum(purchases.mapped('amount_total'))

    def _get_stock_value(self, filters):
        # Match Stock Overview view exactly
        dom = self._get_filter_domain('rv.stock.overview', filters)
        records = self.env['rv.stock.overview'].search(dom)
        return sum(records.mapped('on_hand_qty'))

    def _get_payment_in(self, filters):
        dom = [('payment_type', '=', 'inbound'), ('state', 'not in', ['draft', 'cancel'])] + self._get_filter_domain('account.payment', filters)
        payments = self.env['account.payment'].search(dom)
        return sum(payments.mapped('amount'))

    def _get_advance_given(self, filters):
        dom = [
            ('payment_type', '=', 'outbound'),
            ('partner_type', '=', 'supplier'),
            ('state', 'not in', ['draft', 'cancel'])
        ] + self._get_filter_domain('account.payment', filters)
        payments = self.env['account.payment'].search(dom)
        return sum(payments.mapped('amount'))
        
    def _get_advance_received(self, filters):
        if 'sale_order_id' not in self.env['account.payment']._fields:
            return 0.0
        dom = [
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', 'not in', ['draft', 'cancel']),
            ('sale_order_id', '!=', False)
        ] + self._get_filter_domain('account.payment', filters)
        
        payments = self.env['account.payment'].search(dom)
        return sum(payments.mapped('amount'))

    def _get_yes_bank_incoming(self, filters):
        dom = [('payment_type', '=', 'incoming'), ('name', '!=', 'Balance Inquiry Request')] + self._get_filter_domain('yes.bank.log', filters)
        records = self.env['yes.bank.log'].search(dom)
        return sum(records.mapped('amount'))

    def _get_yes_bank_outgoing(self, filters):
        dom = [('payment_type', '=', 'outgoing')] + self._get_filter_domain('yes.bank.log', filters)
        records = self.env['yes.bank.log'].search(dom)
        return abs(sum(records.mapped('amount')))

    def _get_yes_bank_balance(self, filters):
        journal = self.env['account.journal'].search([('type', '=', 'bank'), ('yes_bank_balance', '!=', False)], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        return journal.yes_bank_balance if journal else 0.0

    def _get_opportunity_dashboard_data(self, filters):
        dom_lead = [('type', '=', 'lead'), ('active', '=', True)] + self._get_filter_domain('crm.lead', filters)
        dom_opp = [('type', '=', 'opportunity'), ('active', '=', True)] + self._get_filter_domain('crm.lead', filters)
        
        open_leads = self.env['crm.lead'].search_count(dom_lead + [('stage_id.is_won', '=', False)])
        open_opps = self.env['crm.lead'].search_count(dom_opp + [('stage_id.is_won', '=', False)])
        
        pipeline = self.env['crm.lead'].search(dom_opp + [('stage_id.is_won', '=', False)])
        pipeline_val = sum(pipeline.mapped('expected_revenue'))
        
        won_count = self.env['crm.lead'].search_count(dom_opp + [('stage_id.is_won', '=', True)])
        
        total_active_opps = self.env['crm.lead'].search_count(dom_opp)
        conversion = (won_count / total_active_opps * 100) if total_active_opps > 0 else 0
        
        win_rate = conversion
        
        won_revenue = sum(self.env['crm.lead'].search(dom_opp + [('stage_id.is_won', '=', True)]).mapped('expected_revenue'))
        avg_deal_size = won_revenue / won_count if won_count else 0
        
        # Charts
        stage_groups = self.env['crm.lead'].read_group(
            dom_opp + [('stage_id.is_won', '=', False)],
            ['stage_id', 'expected_revenue'],
            ['stage_id']
        )
        pipeline_by_stage = {
            'labels': [g['stage_id'][1] for g in stage_groups if g['stage_id']],
            'data': [g['expected_revenue'] for g in stage_groups if g['stage_id']]
        }

        source_groups = self.env['crm.lead'].read_group(
            dom_opp,
            ['source_id'],
            ['source_id']
        )
        source_labels = []
        source_data = []
        for g in source_groups:
             label = g['source_id'][1] if g['source_id'] else 'Unknown'
             source_labels.append(label)
             source_data.append(g['source_id_count'])
             
        opp_by_source = {
            'labels': source_labels,
            'data': source_data
        }

        return {
            'kpis': {
                'open_leads': open_leads,
                'open_opportunities': open_opps,
                'pipeline_value': pipeline_val,
                'lead_conversion': round(conversion, 1),
                'win_rate': round(win_rate, 1),
                'avg_deal_size': round(avg_deal_size, 2)
            },
            'charts': {
                'pipeline_by_stage': pipeline_by_stage,
                'opp_by_source': opp_by_source
            }
        }

    def _get_sales_dashboard_data(self, filters):
        # NOTE: dashboard_filter module is not used here but custom logic.
        
        # Domains
        dom_sale = self._get_filter_domain('sale.order', filters)
        dom_move = self._get_filter_domain('account.move', filters)
        
        draft_quotes = self.env['sale.order'].search_count(dom_sale + [('state', 'in', ['draft', 'sent'])])
        sent_quotes = self.env['sale.order'].search_count(dom_sale + [('state', '=', 'sent')])
        
        confirmed_orders = self.env['sale.order'].search_count(dom_sale + [('state', '=', 'sale'), ('invoice_status', '=', 'to invoice'), ('picking_ids.state', 'not in', ['done', 'cancel'])])
        
        orders = self.env['sale.order'].search(dom_sale + [('state', 'in', ['sale', 'done'])])
        revenue = sum(orders.mapped('amount_total'))
        avg_order = revenue / len(orders) if orders else 0
        
        invoices = self.env['account.move'].search(dom_move + [('move_type', '=', 'out_invoice'), ('state', '!=', 'cancel')])
        invoice_count = len(invoices)
        invoice_revenue = sum(invoices.mapped('amount_total'))
        
        # Charts
        # Trend: 12 Months filtered by range if provided? 
        # Usually trend is historical. If user filters "This Month", trend might show daily?
        # For now, sticking to monthly trend but bounded by the filter's date if present?
        # If date filter is active, read_group automatically respects it via domain.
        
        trend_dom = dom_sale + [('state', 'in', ['sale', 'done'])]
        # If no date filter, we might want to default to last 12 months for the chart?
        # But if user selects "This Month", trend should probably show days? 
        # Keeping it simple: Standard read_group on provided domain.
        
        trend_groups = self.env['sale.order'].read_group(
            trend_dom,
            ['date_order', 'amount_total'],
            ['date_order:month']
        )
        trend_labels = [g['date_order:month'] for g in trend_groups]
        trend_values = [g['amount_total'] for g in trend_groups]
        
        # Products
        # Top 5
        # Search lines matching domain
        # Optimization: Don't fetch all lines. Use read_group on lines.
        # But we need to filter lines by Order domain (e.g. Partner, Date)
        # We can find the order IDs first.
        
        line_domain = []
        if orders:
            line_domain = [('order_id', 'in', orders.ids)]
        else:
            line_domain = [('create_date', '=', '1970-01-01')] # Empty

        top_products = self.env['sale.order.line'].read_group(
            line_domain,
            ['product_id', 'price_subtotal'],
            ['product_id'],
            limit=5,
            orderby='price_subtotal desc'
        )
        
        product_labels = [g['product_id'][1] for g in top_products if g['product_id']]
        product_values = [g['price_subtotal'] for g in top_products if g['product_id']]

        return {
            'kpis': {
                'draft_quotations': draft_quotes,
                'confirmed_orders': confirmed_orders,
                'draft_proformas': 0,
                'invoices': invoice_count,
                'sales_revenue': revenue,
                'avg_order_value': round(avg_order, 2),
                'invoice_revenue': invoice_revenue,
                'sent_quotations': sent_quotes
            },
             'charts': {
                'trend': {'labels': trend_labels, 'data': trend_values},
                'top_products': {'labels': product_labels, 'data': product_values}
            }
        }

    def _get_team_performance(self, filters):
        # We assume filters apply:
        # e.g. If Salesperson filter is set, we only show that user? Or still all users but filtered data?
        # Usually "Team Performance" table shows all users. 
        # If "Salesperson" filter is active, it makes sense to only show that salesperson in the table.
        
        domain_user = [('share', '=', False)]
        if filters.get('user_id'):
            domain_user.append(('id', '=', filters['user_id']))
            
        users = self.env['res.users'].search(domain_user)
        data = []
        
        # For targets/revenue calculation, we use the date filters if provided
        
        for user in users:
            # Revenue
            # We must apply date filters to these metrics
            user_filters = filters.copy()
            user_filters['user_id'] = user.id # Force user
            
            dom_sale = [('state', 'in', ['sale', 'done'])] + self._get_filter_domain('sale.order', user_filters)
            revenue = sum(self.env['sale.order'].search(dom_sale).mapped('amount_total'))

            # Leads & Deals
            dom_lead = [('type', '=', 'lead')] + self._get_filter_domain('crm.lead', user_filters)
            leads = self.env['crm.lead'].search_count(dom_lead)

            dom_opp = [('type', '=', 'opportunity')] + self._get_filter_domain('crm.lead', user_filters)
            deals = self.env['crm.lead'].search_count(dom_opp)

            # Target (Month/Year based on date_to or current?)
            # If date range spans multiple months, target sum?
            # Complexity: Target model is typically monthly.
            # We'll try to find targets matching the filtered period.
            
            target = 0
            if filters.get('date_from'):
                # Basic approximation: Match targets where target month/year is in range?
                # Or just Sum all targets if they have a date?
                # The custom module `rv_sales_target` uses month/year fields (char/int).
                # We'll skip complex target date filtering for now and default to "This Month" logic if no date, or simple lookup.
                pass
            
            # Use current logic if no date filter, else try to sum
            # For simplicity, I'll retain the existing "This Month" target display, 
            # unless the user wants historical targets. 
            # Given the request is just "Add filters", I won't rewrite the target logic too much yet.
            # Let's show target for the current month of the 'End Date' or Today.
            
            ref_date = fields.Date.today()
            if filters.get('date_to'):
                ref_date = fields.Date.from_string(filters.get('date_to'))
                
            month = f"{ref_date.month:02d}"
            year = str(ref_date.year)
            
            target = sum(self.env['sales.target.line'].search([
                ('target_id.user_id', '=', user.id),
                ('month', '=', month),
                ('year', '=', year),
            ]).mapped('target_amount'))

            if revenue or leads or deals or target:
                data.append({
                    'name': user.name,
                    'leads': leads,
                    'deals': deals,
                    'revenue': revenue,
                    'salestarget': target,   
                })

        return sorted(data, key=lambda x: x['revenue'], reverse=True)

    def _get_recent_orders(self, filters):
        dom = [('state', 'in', ['sale', 'done'])] + self._get_filter_domain('sale.order', filters)
        orders = self.env['sale.order'].search(dom, order='date_order desc', limit=10)
        return [{'name': o.name, 'customer': o.partner_id.name, 'amount': o.amount_total, 'date': o.date_order} for o in orders]
        
    def _get_top_deals(self, filters):
        dom = [('type', '=', 'opportunity'), ('stage_id.is_won', '=', False)] + self._get_filter_domain('crm.lead', filters)
        deals = self.env['crm.lead'].search(dom, order='expected_revenue desc', limit=10)
        return [{'name': d.name, 'customer': d.partner_id.name, 'expected_revenue': d.expected_revenue, 'stage': d.stage_id.name, 'probability': d.probability} for d in deals]


    # Lead & Deal Summary
    new_lead = fields.Integer(string='New Lead', compute='_compute_metrics')
    new_deal = fields.Integer(string='New Deal', compute='_compute_metrics')
    won_deal = fields.Integer(string='Won Deal', compute='_compute_metrics')
    won_amount = fields.Float(string='Won Amount', compute='_compute_metrics')

    # Follow-ups Summary
    # Follow-ups Summary
    lead_done_followup = fields.Integer(string='Lead Follow-up', compute='_compute_metrics')
    opportunity_done_followup = fields.Integer(string='Opportunity Follow-up', compute='_compute_metrics')
    overdue_followup = fields.Integer(string='Overdue Follow-up', compute='_compute_metrics')
    tomorrow_followup = fields.Integer(string='Tomorrow Follow-up', compute='_compute_metrics')
    completed_task = fields.Integer(string='Completed Tasks', compute='_compute_metrics')

    # Today's Activity KPIs
    quotation_count_today = fields.Integer(string="Quotations Created", compute='_compute_metrics')
    quotation_amount_today = fields.Float(string="Quotations Amount", compute='_compute_metrics')
    order_confirmed_count_today = fields.Integer(string="Orders Confirmed", compute='_compute_metrics')
    order_confirmed_amount_today = fields.Float(string="Orders Confirmed Amount", compute='_compute_metrics')
    purchase_count_today = fields.Integer(string="Purchase Count", compute='_compute_metrics')
    purchase_amount_today = fields.Float(string="Purchase Amount", compute='_compute_metrics')
    inventory_out_qty_today = fields.Float(string="Inventory Delivered (Qty)", compute='_compute_metrics')
    payment_in_amount_today = fields.Float(string="Payment In (Bank)", compute='_compute_metrics')
    advance_given_amount_today = fields.Float(string="Advance Given", compute='_compute_metrics')
    advance_received_amount_today = fields.Float(string="Advance Received", compute='_compute_metrics')
    invoice_count_today = fields.Integer(string="Invoices Created", compute='_compute_metrics')
    invoice_amount_today = fields.Float(string="Invoiced Amount", compute='_compute_metrics')

    # Lines
    user_summary_today_ids = fields.One2many('crm.daily.report.user.line', 'report_id', string='User Summary (Today)', domain=[('period', '=', 'today')])
    user_summary_mtd_ids = fields.One2many('crm.daily.report.user.line', 'report_id', string='User Summary (Month - Till Date)', domain=[('period', '=', 'mtd')])
    
    lead_status_ids = fields.One2many('crm.daily.report.status.line', 'report_id', string='Lead Status Summary', domain=[('type', '=', 'lead')])
    deal_status_ids = fields.One2many('crm.daily.report.status.line', 'report_id', string='Deal Status Summary', domain=[('type', '=', 'opportunity')])
    source_summary_ids = fields.One2many('crm.daily.report.source.line', 'report_id', string='Source wise Lead Summary')
    
    # Sales Dashboard Metrics
    leads_count = fields.Integer(compute='_compute_metrics')
    opportunities_count = fields.Integer(compute='_compute_metrics')
    pipeline_value = fields.Float(compute='_compute_metrics')
    lead_conversion = fields.Float(string='Lead Conversion %', compute='_compute_metrics')
    confirmed_orders = fields.Integer(compute='_compute_metrics')
    sales_revenue = fields.Float(compute='_compute_metrics')
    avg_order_value = fields.Float(compute='_compute_metrics')
    confirmed_proformas = fields.Integer(compute='_compute_metrics') # Placeholder logic

    salestarget = fields.Float(string="Target")

    @api.depends('date')
    def _compute_metrics(self):
        for record in self:
            today = record.date or fields.Date.today()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())
            
            # Helper domains
            domain_lead = [('type', '=', 'lead')]
            domain_opp = [('type', '=', 'opportunity')]
            
            # LEADS
            record.new_lead = self.env['crm.lead'].search_count(domain_lead + [('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            
            # DEALS
            record.new_deal = self.env['crm.lead'].search_count(domain_opp + [('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            
            won_domain = domain_opp + [('date_closed', '>=', today_start), ('date_closed', '<=', today_end), ('stage_id.is_won', '=', True)]
            won_deals = self.env['crm.lead'].search(won_domain)
            record.won_deal = len(won_deals)
            record.won_amount = sum(won_deals.mapped('expected_revenue'))

            # FOLLOW-UPS (Mail Activity)
            # Done today: This is tricky as activities are deleted when done. We check messages of type 'comment' or 'notification' appearing today? 
            # Or assume standard Odoo 'mark as done' logs a message. 
            # For exact "Done Follow-up", we usually count mail.message generated by activity closure.
            # Simplified: Count messages linked to leads today?
            # Better: Count activities with date_deadline=today and state='done'? No, properties lost.
            # Alternate: Check mail.message for subtype "Activity Done"
             
            # For now, let's look at active activities
            activity_domain = [('res_model', '=', 'crm.lead')]
            
            # Overdue: Deadline < Today
            record.overdue_followup = self.env['mail.activity'].search_count(activity_domain + [('date_deadline', '<', today)])
            
            # Tomorrow: Deadline = Tomorrow
            record.tomorrow_followup = self.env['mail.activity'].search_count(activity_domain + [('date_deadline', '=', today + timedelta(days=1))])
            
            # Completed Tasks / Followups (Today)
            # Using mail.message to find "Activity Done" today
            # Filter by Lead vs Opportunity
            # We fetch messages first
            all_msgs = self.env['mail.message'].search([
                ('model', '=', 'crm.lead'),
                ('date', '>=', today_start),
                ('date', '<=', today_end),
                ('message_type', '=', 'auto_comment') # often used for system messages like activity done
            ])
            
            # Now we need to know if linked record is Lead or Opportunity
            # Batch read
            res_ids = list(set(all_msgs.mapped('res_id')))
            crm_leads = self.env['crm.lead'].browse(res_ids)
            lead_ids = crm_leads.filtered(lambda x: x.type == 'lead').ids
            opp_ids = crm_leads.filtered(lambda x: x.type == 'opportunity').ids
            
            record.lead_done_followup = len(all_msgs.filtered(lambda m: m.res_id in lead_ids))
            record.opportunity_done_followup = len(all_msgs.filtered(lambda m: m.res_id in opp_ids))
            
            # Keeping completed_task as total for backward compatibility or sum
            record.completed_task = record.lead_done_followup + record.opportunity_done_followup

            # SALES METRICS overview
            record.leads_count = self.env['crm.lead'].search_count(domain_lead)
            record.opportunities_count = self.env['crm.lead'].search_count(domain_opp)
            
            mypipeline = self.env['crm.lead'].search(domain_opp + [('stage_id.is_won', '=', False)]) # Active Pipeline
            record.pipeline_value = sum(mypipeline.mapped('expected_revenue'))
            
            # Lead Conversion: Won / (Lost + Won) * 100 ?? or Won / Total Opportunities?
            # Standard formula: Won / (Total Closed) ? 
            # Providing simple Won / All Opportunities for now or dynamic calculation
            all_closed = self.env['crm.lead'].search_count(domain_opp + [('active', '=', False)]) # approximate
            all_won = self.env['crm.lead'].search_count(domain_opp + [('stage_id.is_won', '=', True)])
            record.lead_conversion = (all_won / record.opportunities_count * 100) if record.opportunities_count else 0.0

            # Sales Revenue & Orders (Today or Total?? Dashboard implies Total metrics usually, but "Today" report might want today's?)
            # The screenshots show "Sales Team Dashboard" with Total values (Confirmed Proformas 0, Sales Revenue 0).
            # The top part is "Business Overview Day Report".
            # I will calculate totals for the bottom dashboard Part, and Today's specific where indicated.
            
            all_orders = self.env['sale.order'].search([('state', 'in', ['sale', 'done'])])
            record.confirmed_orders = len(all_orders)
            record.sales_revenue = sum(all_orders.mapped('amount_total'))
            record.avg_order_value = record.sales_revenue / record.confirmed_orders if record.confirmed_orders else 0.0
            
            # Confirmed Proformas
            # Assuming 'draft' orders sent? or invoices?
            record.confirmed_proformas = 0 # Placeholder

            # --- TODAY'S ACTIVITY CALCULATION ---
            
            # 1. Quotations Created Today (Draft/Sent created today)
            quotes_today = self.env['sale.order'].search([
                ('create_date', '>=', today_start),
                ('create_date', '<=', today_end),
                ('state', 'in', ['draft', 'sent'])
            ])
            record.quotation_count_today = len(quotes_today)
            record.quotation_amount_today = sum(quotes_today.mapped('amount_total'))
            
            # 2. Orders Confirmed Today (date_order is confirmation date)
            orders_today = self.env['sale.order'].search([
                ('date_order', '>=', today_start),
                ('date_order', '<=', today_end),
                ('state', 'in', ['sale', 'done'])
            ])
            record.order_confirmed_count_today = len(orders_today)
            record.order_confirmed_amount_today = sum(orders_today.mapped('amount_total'))
            
            # 3. Purchase Ordered Today (Confirmed purchases)
            purchases_today = self.env['purchase.order'].search([
                ('date_approve', '>=', today_start),
                ('date_approve', '<=', today_end),
                ('state', 'in', ['purchase', 'done'])
            ])
            record.purchase_count_today = len(purchases_today)
            record.purchase_amount_today = sum(purchases_today.mapped('amount_total'))
            
            # 4. Inventory Gone (Delivered)
            # Find outgoing pickings done today
            outgoing_moves = self.env['stock.move'].search([
                ('date', '>=', today_start), # date field on move is execution date
                ('date', '<=', today_end),
                ('state', '=', 'done'),
                ('picking_code', '=', 'outgoing')
            ])
            record.inventory_out_qty_today = sum(outgoing_moves.mapped('product_uom_qty'))
            
            # 5. Payment In (Bank)
            in_payments = self.env['account.payment'].search([
                ('date', '=', today),
                ('payment_type', '=', 'inbound'),
                ('state', 'not in', ['draft', 'cancel'])
            ])
            record.payment_in_amount_today = sum(in_payments.mapped('amount'))
            
            # 6. Advance Given
            adv_given = self.env['account.payment'].search([
                ('date', '=', today),
                ('payment_type', '=', 'outbound'),
                ('partner_type', '=', 'supplier'),
                ('state', 'not in', ['draft', 'cancel'])
            ])
            record.advance_given_amount_today = sum(adv_given.mapped('amount'))
            
            # 7. Advance Received
            # Assuming logic matches dashboard: Inbound, Customer, Linked to Sale Order? Or just all advances?
            # Dashboard logic: inbound, customer, sale_order_id != False
            # We strictly stick to dashboard logic if possible.
            adv_params = [
                ('date', '=', today),
                ('payment_type', '=', 'inbound'),
                ('partner_type', '=', 'customer'),
                ('state', 'not in', ['draft', 'cancel'])
            ]
            if 'sale_order_id' in self.env['account.payment']._fields:
               adv_params.append(('sale_order_id', '!=', False))
               
            adv_received = self.env['account.payment'].search(adv_params)
            record.advance_received_amount_today = sum(adv_received.mapped('amount'))
            
            # 8. Create Invoice (Invoiced Today)
            todays_invoices = self.env['account.move'].search([
                ('invoice_date', '=', today),
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel')
            ])
            record.invoice_count_today = len(todays_invoices)
            record.invoice_amount_today = sum(todays_invoices.mapped('amount_total'))

            # Populate One2many lines (Metrics calculation needs to be done explicitly or via separate compute)
            # To avoid complex onchange, we can call a method to generate lines
    
    def action_generate_report_lines(self):
        self.ensure_one()
        today = self.date
        month_start = today.replace(day=1)
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # CLEAR EXISTING
        self.user_summary_today_ids.unlink()
        self.user_summary_mtd_ids.unlink()
        self.lead_status_ids.unlink()
        self.deal_status_ids.unlink()
        
        # 1. USER SUMMARY
        users = self.env['res.users'].search([('share', '=', False)]) # Internal users
        
        # Pre-fetch data to optimize? For now simple loop
        for user in users:
            # TODAY
            # Untouched: Assigned new leads, not unmodified today? 
            # Lets define Untouched as: Leads assigned to user, status='New', write_date < Today (creation was before today?)
            # Or Lead assigned today and no activity?
            # I'll stick to: Leads assigned to user, currently in state 'New' (first stage).
            # The screenshot shows Untouched Lead count.
            
            # New Leads Today
            leads_today = self.env['crm.lead'].search_count([('user_id', '=', user.id), ('type', '=', 'lead'), ('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            
            # Deals Today
            deals_today = self.env['crm.lead'].search_count([('user_id', '=', user.id), ('type', '=', 'opportunity'), ('create_date', '>=', today_start), ('create_date', '<=', today_end)])

            # Done Followups Today - Split
            # Re-using logic: messages created by user today
            user_msgs = self.env['mail.message'].search([
                ('model', '=', 'crm.lead'),
                ('create_uid', '=', user.id),
                ('date', '>=', today_start),
                ('date', '<=', today_end)
            ])
            # Determine type
            u_res_ids = list(set(user_msgs.mapped('res_id')))
            u_leads = self.env['crm.lead'].browse(u_res_ids)
            u_lead_type_ids = u_leads.filtered(lambda x: x.type == 'lead').ids
            u_opp_type_ids = u_leads.filtered(lambda x: x.type == 'opportunity').ids
            
            lead_done_msgs = len(user_msgs.filtered(lambda m: m.res_id in u_lead_type_ids))
            opp_done_msgs = len(user_msgs.filtered(lambda m: m.res_id in u_opp_type_ids))
            
            # Revenue Today (Sales Orders confirmed today)
            revenue_today = sum(self.env['sale.order'].search([
                ('user_id', '=', user.id),
                ('date_order', '>=', today_start),
                ('date_order', '<=', today_end),
                ('state', 'in', ['sale', 'done'])
            ]).mapped('amount_total'))
            
            self.env['crm.daily.report.user.line'].create({
                'report_id': self.id,
                'period': 'today',
                'user_id': user.id,
                'untouched_lead': 0, # Logic generic
                'lead': leads_today,
                'deal': deals_today,
                'lead_done_followup': lead_done_msgs,
                'opportunity_done_followup': opp_done_msgs,
                'revenue': revenue_today
            })

            # MTD
            leads_mtd = self.env['crm.lead'].search_count([('user_id', '=', user.id), ('type', '=', 'lead'), ('create_date', '>=', month_start)])
            deals_mtd = self.env['crm.lead'].search_count([('user_id', '=', user.id), ('type', '=', 'opportunity'), ('create_date', '>=', month_start)])
            
             # Revenue MTD
            revenue_mtd = sum(self.env['sale.order'].search([
                ('user_id', '=', user.id),
                ('date_order', '>=', month_start),
                ('state', 'in', ['sale', 'done'])
            ]).mapped('amount_total'))
            
            # Sales Target (Month)
            # Assuming 'sales.target.line' model exists as per previous context
            month_str = f"{today.month:02d}"
            year_str = str(today.year)
            
            try:
                target_amount = sum(self.env['sales.target.line'].search([
                    ('target_id.user_id', '=', user.id),
                    ('month', '=', month_str),
                    ('year', '=', year_str),
                ]).mapped('target_amount'))
            except Exception:
                target_amount = 0.0

            self.env['crm.daily.report.user.line'].create({
                'report_id': self.id,
                'period': 'mtd',
                'user_id': user.id,
                'untouched_lead': 0,
                'lead': leads_mtd,
                'deal': deals_mtd,
                'lead_done_followup': 0, 
                'opportunity_done_followup': 0,
                'revenue': revenue_mtd
            })

        # 2. STATUS SUMMARY (Leads & Deals)
        stages = self.env['crm.stage'].search([])
        for stage in stages:
            # We need to separate Lead stages from Opportunity stages? 
            # In Odoo stages are shared but often configured with logic. 
            # Standard Odoo: checks 'on_change' or Team domain.
            # We will query counting leads vs opportunities for each stage.
            
            # LEAD
            l_today = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'lead'), ('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            l_mtd = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'lead'), ('create_date', '>=', month_start)])
            l_life = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'lead')])
            
            if l_life > 0 or l_today > 0:
                self.env['crm.daily.report.status.line'].create({
                    'report_id': self.id,
                    'type': 'lead',
                    'stage_id': stage.id,
                    'today_count': l_today,
                    'mtd_count': l_mtd,
                    'lifetime_count': l_life
                })
                
            # DEAL
            d_today = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'opportunity'), ('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            d_mtd = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'opportunity'), ('create_date', '>=', month_start)])
            d_life = self.env['crm.lead'].search_count([('stage_id', '=', stage.id), ('type', '=', 'opportunity')])
            
            if d_life > 0 or d_today > 0:
                self.env['crm.daily.report.status.line'].create({
                   'report_id': self.id,
                    'type': 'opportunity',
                    'stage_id': stage.id,
                    'today_count': d_today,
                    'mtd_count': d_mtd,
                    'lifetime_count': d_life
                })

        # 3. SOURCE SUMMARY
        sources = self.env['utm.source'].search([])
        # Also need to handle 'False' source? Odoo usually has records. 
        # But utm.source might be empty if not used. 
        # Optimization: group by query. For now, iterate or use read_group.
        
        # Using read_group is better for performance but "Source wise Lead Summary these all contain".
        # Assuming we want Lead + Opp or just Lead? Text says "Lead Summary".
        # I'll include both or just type='lead'. Usually "Lead Sources" implies origin.
        
        # Let's do a group by query for efficiency
        domain = [('create_date', '>=', today_start), ('create_date', '<=', today_end)] 
        # Wait, usually a summary includes historical data? The other tables have MTD and Lifetime.
        # Screenshot for Lead Status has Today, MTD, Lifetime.
        # I will assume Source Summary needs the same structure.
        
        # Get all sources used
        # We can iterate all sources, or just those with leads.
        
        used_source_ids = self.env['crm.lead'].read_group([], ['source_id'], ['source_id'])
        source_ids = [s['source_id'][0] for s in used_source_ids if s['source_id']]
        
        # Add those not in result if we want ALL sources? No, just used ones.
        
        for source_id in source_ids:
            source = self.env['utm.source'].browse(source_id)
            
            s_today = self.env['crm.lead'].search_count([('source_id', '=', source.id), ('create_date', '>=', today_start), ('create_date', '<=', today_end)])
            s_life = self.env['crm.lead'].search_count([('source_id', '=', source.id)])
            self.env['crm.daily.report.source.line'].create({
                'report_id': self.id,
                'source_id': source.id,
                'today_count': s_today,
                'lifetime_count': s_life
            })

    def print_report(self):
        self.action_generate_report_lines()
        return self.env.ref('crm_whatsapp.action_report_daily_business_overview').report_action(self)

class DailyReportUserLine(models.TransientModel):
    _name = 'crm.daily.report.user.line'
    _description = 'Daily Report User Summary'

    report_id = fields.Many2one('crm.daily.report')
    currency_id = fields.Many2one('res.currency', related='report_id.currency_id', string='Currency', readonly=True)
    period = fields.Selection([('today', 'Today'), ('mtd', 'Month to Date')], required=True)
    user_id = fields.Many2one('res.users', string='User')
    untouched_lead = fields.Integer(string='Untouched Lead')
    lead = fields.Integer(string='Lead')
    deal = fields.Integer(string='Deal')
    lead_done_followup = fields.Integer(string="Lead Follow Up's")
    opportunity_done_followup = fields.Integer(string="Opportunity Follow Up's")
    revenue = fields.Float(string='Revenue')

class DailyReportStatusLine(models.TransientModel):
    _name = 'crm.daily.report.status.line'
    _description = 'Daily Report Status Summary'
    _order = 'today_count desc'

    report_id = fields.Many2one('crm.daily.report')
    stage_id = fields.Many2one('crm.stage', string='Status')
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Deal')], required=True)
    today_count = fields.Integer(string='Today')
    mtd_count = fields.Integer(string='Month Till Date')
    lifetime_count = fields.Integer(string='Life Time')

class DailyReportSourceLine(models.TransientModel):
    _name = 'crm.daily.report.source.line'
    _description = 'Daily Report Source Summary'
    _order = 'today_count desc'

    report_id = fields.Many2one('crm.daily.report')
    source_id = fields.Many2one('utm.source', string='Source')
    today_count = fields.Integer(string='Today')
    lifetime_count = fields.Integer(string='Life Time')
