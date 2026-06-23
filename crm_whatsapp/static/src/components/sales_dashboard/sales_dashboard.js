/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, useState, onWillStart, useRef, useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
const { DateTime } = luxon;

export class SalesDashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.pipelineChartRef = useRef("pipelineChart");
        this.sourceChartRef = useRef("sourceChart");
        this.trendChartRef = useRef("trendChart");
        this.productChartRef = useRef("productChart");

        const isReturning = browser.sessionStorage.getItem('sales_dashboard_returning') === 'true';
        browser.sessionStorage.removeItem('sales_dashboard_returning');
        this.isReturning = isReturning;

        this.state = useState({
            kpis: [],
            team_performance: [],
            recent_orders: [],
            top_deals: [],

            opportunity_dashboard: { kpis: {}, charts: {} },
            sales_dashboard: { kpis: {}, charts: {} },

            activeTab: isReturning ? (browser.sessionStorage.getItem('sales_dashboard_active_tab') || 'overview') : 'overview',

            // FILTERS
            filters: isReturning ? this.getStoredFilters() : this.getDefaultFilters(),

            // Master Data for Dropdowns
            master_data: {
                users: [],
                teams: [],
                countries: [],
                states: [],
                categories: [],
                sources: [],
                products: [],
                customers: []
            }
        });

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js");
            await this.fetchMasterData();
            if (!this.isReturning) {
                this.setPeriod('all'); // Initialize dates to All Time only if fresh load
            }
            await this.fetchData();
        });

        useEffect(() => {
            this.renderCharts();
        }, () => [this.state.activeTab, this.state.sales_dashboard, this.state.opportunity_dashboard]);
    }

    getStoredFilters() {
        const savedFilters = browser.sessionStorage.getItem('sales_dashboard_filters');
        if (savedFilters) {
            return JSON.parse(savedFilters);
        }
        return this.getDefaultFilters();
    }

    getDefaultFilters() {
        return {
            period: 'this_month',
            date_from: null,
            date_to: null,
            user_id: "",
            customer_name: "",
            state_id: "",
            city: "",
            product_name: "",
            source_id: "",
            medium_id: ""
        };
    }

    async fetchMasterData() {
        try {
            // Optimizing fetches: fetch only needed fields
            const users = await this.orm.searchRead('res.users', [['share', '=', false]], ['id', 'name']);
            const states = await this.orm.searchRead('res.country.state', [], ['id', 'name', 'country_id']);
            const sources = await this.orm.searchRead('utm.source', [], ['id', 'name']);

            this.state.master_data = { users, states, sources, products: [], customers: [] };
        } catch (e) {
            console.error("Error fetching master data", e);
        }
    }

    setPeriod(period) {
        this.state.filters.period = period;
        // Basic luxon usage if available in Odoo environment (usually is globally or via module)
        // If luxon is not available, we use standard JS Date objects.
        // Odoo 16+ uses luxon.

        const today = DateTime.local();
        let start, end;

        switch (period) {
            case 'all':
                this.state.filters.date_from = null;
                this.state.filters.date_to = null;
                return; // Exit early, no dates to set
            case 'today':
                start = today.startOf('day');
                end = today.endOf('day');
                break;
            case 'yesterday':
                start = today.minus({ days: 1 }).startOf('day');
                end = today.minus({ days: 1 }).endOf('day');
                break;
            case 'this_week':
                start = today.startOf('week');
                end = today.endOf('week');
                break;
            case 'last_week':
                start = today.minus({ weeks: 1 }).startOf('week');
                end = today.minus({ weeks: 1 }).endOf('week');
                break;
            case 'this_month':
                start = today.startOf('month');
                end = today.endOf('month');
                break;
            case 'last_month':
                start = today.minus({ months: 1 }).startOf('month');
                end = today.minus({ months: 1 }).endOf('month');
                break;
            case 'this_quarter':
                start = today.startOf('quarter');
                end = today.endOf('quarter');
                break;
            case 'last_quarter':
                start = today.minus({ quarters: 1 }).startOf('quarter');
                end = today.minus({ quarters: 1 }).endOf('quarter');
                break;
            case 'this_year':
                start = today.startOf('year');
                end = today.endOf('year');
                break;
            case 'last_90_days':
                start = today.minus({ days: 90 }).startOf('day');
                end = today.endOf('day');
                break;
            case 'custom':
                // Do not modify dates. Keep existing or let user set them.
                return;
        }

        if (start && end) {
            this.state.filters.date_from = start.toISODate();
            this.state.filters.date_to = end.toISODate();
        }
    }

    async onFilterChange(key, value) {
        this.state.filters[key] = value;
        if (key === 'period' && value !== 'custom') {
            this.setPeriod(value);
        }

        browser.sessionStorage.setItem('sales_dashboard_filters', JSON.stringify(this.state.filters));

        // Search customers if typing (min 3 chars or empty to reset)
        if (key === 'customer_name') {
            if (this.searchTimeout) clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(async () => {
                if (value.length > 2) {
                    const customers = await this.orm.searchRead('res.partner', [['name', 'ilike', value]], ['id', 'name'], { limit: 20 });
                    this.state.master_data.customers = customers;
                } else if (value.length === 0) {
                    this.state.master_data.customers = [];
                }
            }, 300);
        }

        // Search products if typing
        if (key === 'product_name') {
            if (this.productSearchTimeout) clearTimeout(this.productSearchTimeout);
            this.productSearchTimeout = setTimeout(async () => {
                if (value.length > 2) {
                    const products = await this.orm.searchRead('product.product', [['name', 'ilike', value]], ['id', 'name'], { limit: 20 });
                    this.state.master_data.products = products;
                } else if (value.length === 0) {
                    this.state.master_data.products = [];
                }
            }, 300);
        }

        await this.fetchData();
    }

    getBackendFilters() {
        const backendFilters = {};
        for (const [k, v] of Object.entries(this.state.filters)) {
            if (v && v !== "") {
                if (k === 'customer_name' || k === 'product_name' || k === 'city' || k === 'date_from' || k === 'date_to' || k === 'period') {
                    backendFilters[k] = v;
                } else {
                    backendFilters[k] = parseInt(v) || v;
                }
            }
        }
        return backendFilters;
    }

    async fetchData() {
        const backendFilters = this.getBackendFilters();
        // Pass filters to backend
        const data = await this.orm.call("crm.daily.report", "get_dashboard_data", [], { filters: backendFilters });
        const kpis = data.kpis;

        this.state.kpis = [
            { name: 'leads', label: 'Leads', value: kpis.leads_count, icon: 'fa-users', color: '#4834d4' },
            { name: 'opportunities', label: 'Opportunities', value: kpis.opportunities_count, icon: 'fa-rocket', color: '#f0932b' },
            { name: 'revenue', label: 'Sales Revenue', value: this.formatCurrency(kpis.sales_revenue), icon: 'fa-inr', color: '#2ecc71' },
            { name: 'purchase', label: 'Purchase Total', value: this.formatCurrency(kpis.purchase_total), icon: 'fa-shopping-cart', color: '#3498db' },
            { name: 'stock', label: 'On Hand Stock', value: kpis.stock_value, icon: 'fa-cubes', color: '#9b59b6' },
            { name: 'payment_in', label: 'Payment In Bank', value: this.formatCurrency(kpis.payment_in), icon: 'fa-bank', color: '#1abc9c' },
            { name: 'advance_given', label: 'Advance Given', value: this.formatCurrency(kpis.advance_given), icon: 'fa-paper-plane', color: '#e67e22' },
            { name: 'advance_received', label: 'Advance Received', value: this.formatCurrency(kpis.advance_received), icon: 'fa-money', color: '#9b59b6' },
            { name: 'yes_bank_incoming', label: 'YES Bank Incoming', value: this.formatCurrency(kpis.yes_bank_incoming), icon: 'fa-bank', color: '#1abc9c' },
            { name: 'yes_bank_outgoing', label: 'YES Bank Outgoing', value: this.formatCurrency(kpis.yes_bank_outgoing), icon: 'fa-bank', color: '#e74c3c' },
            { name: 'yes_bank_balance', label: 'YES Bank Balance', value: this.formatCurrency(kpis.yes_bank_balance), icon: 'fa-bank', color: '#2e86de' },
            { name: 'pipeline', label: 'Pipeline Value', value: this.formatCurrency(kpis.pipeline_value), icon: 'fa-line-chart', color: '#2e86de' },
            { name: 'conversion', label: 'Lead Conversion', value: kpis.lead_conversion + '%', icon: 'fa-bullseye', color: '#00b894' },
            { name: 'orders', label: 'Confirmed Orders', value: kpis.confirmed_orders, icon: 'fa-check-square-o', color: '#f39c12' },
            { name: 'avg_order', label: 'Avg. Order Value', value: this.formatCurrency(kpis.avg_order_value), icon: 'fa-balance-scale', color: '#34495e' },
            { name: 'invoices', label: 'Invoices', value: kpis.invoices, icon: 'fa-file-text-o', color: '#7f8c8d' },
        ];

        this.state.team_performance = data.team_performance;
        this.state.recent_orders = data.recent_orders;
        this.state.top_deals = data.top_deals;
        this.state.opportunity_dashboard = data.opportunity_dashboard;
        this.state.sales_dashboard = data.sales_dashboard;

        // Render charts after data update
        this.renderCharts();
    }

    renderCharts() {
        if (this.state.activeTab === 'opportunities') {
            this.renderPipelineChart();
            this.renderSourceChart();
        } else if (this.state.activeTab === 'revenue') {
            this.renderTrendChart();
            this.renderProductChart();
        }
    }

    renderPipelineChart() {
        setTimeout(() => {
            if (!this.pipelineChartRef.el) return;
            const ctx = this.pipelineChartRef.el.getContext('2d');
            if (this.pipelineChartInstance) this.pipelineChartInstance.destroy();

            this.pipelineChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: this.state.opportunity_dashboard.charts.pipeline_by_stage.labels,
                    datasets: [{
                        label: 'Expected Revenue',
                        data: this.state.opportunity_dashboard.charts.pipeline_by_stage.data,
                        backgroundColor: '#6c5ce7',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }, 100);
    }

    renderSourceChart() {
        setTimeout(() => {
            if (!this.sourceChartRef.el) return;
            const ctx = this.sourceChartRef.el.getContext('2d');
            if (this.sourceChartInstance) this.sourceChartInstance.destroy();

            this.sourceChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: this.state.opportunity_dashboard.charts.opp_by_source.labels,
                    datasets: [{
                        data: this.state.opportunity_dashboard.charts.opp_by_source.data,
                        backgroundColor: ['#fdcb6e', '#e17055', '#00b894', '#0984e3', '#b2bec3'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }, 100);
    }

    renderTrendChart() {
        setTimeout(() => {
            if (!this.trendChartRef.el) return;
            const ctx = this.trendChartRef.el.getContext('2d');
            if (this.trendChartInstance) this.trendChartInstance.destroy();

            this.trendChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: this.state.sales_dashboard.charts.trend.labels,
                    datasets: [{
                        label: 'Sales Revenue',
                        data: this.state.sales_dashboard.charts.trend.data,
                        borderColor: '#00b894',
                        tension: 0.1,
                        fill: true,
                        backgroundColor: 'rgba(0, 184, 148, 0.1)'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }, 100);
    }

    renderProductChart() {
        setTimeout(() => {
            if (!this.productChartRef.el) return;
            const ctx = this.productChartRef.el.getContext('2d');
            if (this.productChartInstance) this.productChartInstance.destroy();

            this.productChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: this.state.sales_dashboard.charts.top_products.labels,
                    datasets: [{
                        label: 'Revenue',
                        data: this.state.sales_dashboard.charts.top_products.data,
                        backgroundColor: '#fdcb6e',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y' }
            });
        }, 100);
    }

    setTab(tab) {
        this.state.activeTab = tab;
        browser.sessionStorage.setItem('sales_dashboard_active_tab', tab);
    }

    formatCurrency(value) {
        return "₹" + (value || 0).toLocaleString('en-IN');
    }

    async refresh() {
        await this.fetchData();
    }

    async openDailyReport() {
        browser.sessionStorage.setItem('sales_dashboard_returning', 'true');
        this.actionService.doAction("crm_whatsapp.action_crm_daily_report");
    }

    async openKpi(name) {
        let action = {};
        switch (name) {
            case 'leads':
                action = { name: "Leads", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'lead']], context: { 'default_type': 'lead' } };
                break;
            case 'opportunities':
                action = { name: "Opportunities", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'opportunity']], context: { 'default_type': 'opportunity' } };
                break;
            case 'pipeline':
            case 'pipeline_value':
                action = { name: "Pipeline", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'opportunity'], ['stage_id.is_won', '=', false]], context: { 'default_type': 'opportunity' } };
                break;
            case 'conversion':
            case 'lead_conversion':
            case 'win_rate':
                action = { name: "Won Opportunities", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'opportunity'], ['stage_id.is_won', '=', true]], context: { 'default_type': 'opportunity' } };
                break;
            case 'orders':
            case 'confirmed_orders':
                action = { name: "Confirmed Orders", type: "ir.actions.act_window", res_model: "sale.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', '=', 'sale'], ['invoice_status', '=', 'to invoice'], ['picking_ids.state', 'not in', ['done', 'cancel']]] };
                break;
            case 'revenue':
            case 'sales_revenue':
            case 'avg_order':
            case 'avg_order_value':
            case 'avg_deal_size':
                action = { name: "Sales Orders", type: "ir.actions.act_window", res_model: "sale.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', 'in', ['sale', 'done']]] };
                break;
            case 'proformas':
            case 'confirmed_proformas':
            case 'invoices':
                action = { name: "Invoices", type: "ir.actions.act_window", res_model: "account.move", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['move_type', '=', 'out_invoice'], ['state', '!=', 'cancel']], context: { 'default_move_type': 'out_invoice' } };
                break;
            case 'open_leads':
                action = { name: "Open Leads", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'lead'], ['stage_id.is_won', '=', false]], context: { 'default_type': 'lead' } };
                break;
            case 'open_opportunities':
                action = { name: "Open Opportunities", type: "ir.actions.act_window", res_model: "crm.lead", view_mode: "list,kanban,form", views: [[false, "list"], [false, "kanban"], [false, "form"]], domain: [['type', '=', 'opportunity'], ['stage_id.is_won', '=', false]], context: { 'default_type': 'opportunity' } };
                break;
            case 'draft_quotations':
                action = { name: "Draft Quotations", type: "ir.actions.act_window", res_model: "sale.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', 'in', ['draft', 'sent']]] };
                break;
            case 'draft_proformas':
                action = { name: "Draft Proformas", type: "ir.actions.act_window", res_model: "sale.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', '=', 'draft']] };
                break;
            case 'sent_quotations':
                action = { name: "Sent Quotations", type: "ir.actions.act_window", res_model: "sale.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', '=', 'sent']] };
                break;
            case 'proforma_revenue':
            case 'invoice_revenue':
                action = { name: "Invoice Revenue", type: "ir.actions.act_window", res_model: "account.move", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['move_type', '=', 'out_invoice'], ['state', '!=', 'cancel']], context: { 'default_move_type': 'out_invoice' } };
                break;
            case 'purchase':
                action = { name: "Purchase Orders", type: "ir.actions.act_window", res_model: "purchase.order", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['state', 'in', ['purchase', 'done']]] };
                break;
            case 'stock':
                action = { name: "Stock Overview", type: "ir.actions.act_window", res_model: "rv.stock.overview", view_mode: "list", views: [[false, "list"]] };
                break;
            case 'payment_in':
                action = { name: "Payments In (Bank)", type: "ir.actions.act_window", res_model: "account.payment", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['payment_type', '=', 'inbound'], ['state', 'not in', ['draft', 'cancel']]] };
                break;
            case 'advance_given':
                action = { name: "Advance Payments Given", type: "ir.actions.act_window", res_model: "account.payment", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['payment_type', '=', 'outbound'], ['partner_type', '=', 'supplier'], ['state', 'not in', ['draft', 'cancel']]] };
                break;
            case 'advance_received':
                action = { name: "Advance Payments Received", type: "ir.actions.act_window", res_model: "account.payment", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['payment_type', '=', 'inbound'], ['partner_type', '=', 'customer'], ['state', 'not in', ['draft', 'cancel']], ['sale_order_id', '!=', false]] };
                break;
            case 'yes_bank_incoming':
                action = { name: "YES Bank Incoming", type: "ir.actions.act_window", res_model: "yes.bank.log", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['payment_type', '=', 'incoming']] };
                break;
            case 'yes_bank_outgoing':
                action = { name: "YES Bank Outgoing", type: "ir.actions.act_window", res_model: "yes.bank.log", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['payment_type', '=', 'outgoing']] };
                break;
            case 'yes_bank_balance':
                action = { name: "YES Bank Journal", type: "ir.actions.act_window", res_model: "account.journal", view_mode: "list,form", views: [[false, "list"], [false, "form"]], domain: [['type', '=', 'bank']] };
                break;
        }

        if (action.res_model) {
            try {
                const backendFilters = this.getBackendFilters();
                const filterDomain = await this.orm.call("crm.daily.report", "get_context_domain", [action.res_model], { filters: backendFilters });

                if (filterDomain && filterDomain.length > 0) {
                    action.domain = (action.domain || []).concat(filterDomain);
                }

                browser.sessionStorage.setItem('sales_dashboard_returning', 'true');
                this.actionService.doAction(action);
            } catch (e) {
                console.error("Error applying filters to action", e);
                // Fallback: open without additional filters
                browser.sessionStorage.setItem('sales_dashboard_returning', 'true');
                this.actionService.doAction(action);
            }
        }
    }
}

SalesDashboard.template = "crm_whatsapp.SalesDashboard";

registry.category("actions").add("crm_whatsapp.sales_dashboard_client_action", SalesDashboard);
