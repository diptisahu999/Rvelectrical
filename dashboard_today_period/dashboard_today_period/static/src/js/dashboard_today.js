import { registry } from "@web/core/registry";
import {
  Component,
  useState,
  onWillStart,
  onMounted,
  onWillUnmount,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DashboardTodayExtension extends Component {
  setup() {
    this.orm = useService("orm");
    this.state = useState({
      selectedPeriod: "last_90_days",
      dashboardData: {},
      chartData: [],
    });

    onWillStart(async () => {
      await this.loadDashboardData();
    });

    // Ensure DOM hooks are installed when the view is mounted
    onMounted(() => {
      this.installDomHooks();
    });

    onWillUnmount(() => {
      if (this._observer) {
        this._observer.disconnect();
        this._observer = undefined;
      }
      if (this._selectEl && this._onSelectChange) {
        this._selectEl.removeEventListener("change", this._onSelectChange);
      }
    });
  }

  installDomHooks() {
    // Add Today option and attach listeners
    this.addTodayOption();

    // Attach to native <select> if present
    const selectEl = document.querySelector(".period-dropdown");
    if (selectEl) {
      this._selectEl = selectEl;
      this._onSelectChange = (ev) => this.onPeriodChange(ev);
      selectEl.addEventListener("change", this._onSelectChange, {
        passive: true,
      });
    }

    // Observe DOM to re-inject Today into dropdown menus that render late
    if (!this._observer) {
      this._observer = new MutationObserver(() => this.addTodayOption());
      this._observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  addTodayOption() {
    // 1) Native <select> support
    const selectEl = document.querySelector(".period-dropdown");
    if (selectEl) {
      const hasToday = Array.from(selectEl.options).some(
        (o) => o.value === "today"
      );
      if (!hasToday) {
        const opts = Array.from(selectEl.options);
        const ytdIndex = opts.findIndex(
          (o) => (o.textContent || "").trim().toLowerCase() === "year to date"
        );
        const todayOption = new Option("Today", "today");
        if (ytdIndex >= 0) {
          selectEl.add(todayOption, ytdIndex + 1);
        } else {
          selectEl.add(todayOption, 0);
        }
      }
      return; // If a select exists, we don't need to handle menu case for this view
    }

    // 2) Dropdown menu (Odoo UI) support
    const menus = document.querySelectorAll(
      ".dropdown-menu, .o_dropdown_menu, .o-dropdown--menu"
    );
    menus.forEach((menu) => {
      if (!menu || menu.querySelector('[data-dashboard-period="today"]')) {
        return;
      }

      const items = Array.from(
        menu.querySelectorAll(
          ".dropdown-item, .o_menu_item, li > a, li > button"
        )
      );
      const yearToDateItem = items.find(
        (el) => (el.textContent || "").trim().toLowerCase() === "year to date"
      );
      if (!yearToDateItem) {
        return;
      }

      const todayItem = yearToDateItem.cloneNode(true);
      todayItem.textContent = "Today";
      todayItem.setAttribute("data-dashboard-period", "today");
      todayItem.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.selectedPeriod = "today";
        // Update the toggle/label if we can find it
        const toggle = menu
          .closest(".dropdown, .o_dropdown, .o-dropdown")
          ?.querySelector(
            ".dropdown-toggle, .o_dropdown_toggler, .o-dropdown--toggle"
          );
        if (toggle) {
          toggle.textContent = "Today";
        }
        this.loadDashboardData();
      });

      // Insert right after Year to Date
      const parent = yearToDateItem.parentElement || menu;
      if (yearToDateItem.nextSibling) {
        parent.insertBefore(todayItem, yearToDateItem.nextSibling);
      } else {
        parent.appendChild(todayItem);
      }
    });
  }

  async onPeriodChange(event) {
    this.state.selectedPeriod = event.target.value;
    await this.loadDashboardData();
  }

  async loadDashboardData() {
    try {
      if (this.state.selectedPeriod === "today") {
        const data = await this.orm.call(
          "dashboard.today",
          "get_today_sales_data",
          []
        );
        const chartData = await this.orm.call(
          "dashboard.today",
          "get_today_chart_data",
          []
        );

        this.state.dashboardData = data;
        this.state.chartData = chartData;

        // Update the dashboard display
        this.updateDashboardDisplay();
        this.updateChart();
      }
    } catch (error) {
      console.error("Error loading today dashboard data:", error);
    }
  }

  updateDashboardDisplay() {
    const data = this.state.dashboardData;

    // Update the main metrics
    const invoicedElement = document.querySelector(".invoiced-amount");
    const avgInvoiceElement = document.querySelector(".avg-invoice-amount");
    const dsoElement = document.querySelector(".dso-days");

    if (invoicedElement) invoicedElement.textContent = data.invoiced || "0";
    if (avgInvoiceElement)
      avgInvoiceElement.textContent = data.average_invoice || "0";
    if (dsoElement) dsoElement.textContent = "Today";

    // Update unpaid count
    const unpaidElement = document.querySelector(".unpaid-count");
    if (unpaidElement)
      unpaidElement.textContent = `${data.unpaid_count || 0} unpaid`;

    // Update invoices count
    const invoicesCountElement = document.querySelector(".invoices-count");
    if (invoicesCountElement)
      invoicesCountElement.textContent = `${data.total_invoices || 0} Invoices`;

    // Update top invoices table
    this.updateTopInvoicesTable();
  }

  updateTopInvoicesTable() {
    const tableBody = document.querySelector(".top-invoices-table tbody");
    if (!tableBody || !this.state.dashboardData.top_invoices) return;

    tableBody.innerHTML = "";

    this.state.dashboardData.top_invoices.forEach((invoice) => {
      const row = document.createElement("tr");
      row.innerHTML = `
                <td>${invoice.reference}</td>
                <td>${invoice.salesperson}</td>
                <td>${invoice.status}</td>
                <td>${invoice.customer}</td>
                <td>${invoice.date}</td>
                <td>₹${invoice.amount.toFixed(2)}</td>
            `;
      tableBody.appendChild(row);
    });
  }

  updateChart() {
    // Update the chart with hourly data for today
    const chartContainer = document.querySelector(".chart-container");
    if (!chartContainer) return;

    // Simple chart update - you can integrate with your existing chart library
    const chartData = this.state.chartData;

    if (chartData.length > 0) {
      // Update chart with hourly breakdown
      this.renderTodayChart(chartData);
    }
  }

  renderTodayChart(data) {
    // This is a basic implementation - adapt based on your chart library
    const chartContainer = document.querySelector(".chart-container canvas");
    if (!chartContainer) return;

    const ctx = chartContainer.getContext("2d");

    // Clear previous chart
    ctx.clearRect(0, 0, chartContainer.width, chartContainer.height);

    // Simple bar chart for hourly data
    const maxAmount = Math.max(...data.map((d) => d.amount));
    const barWidth = chartContainer.width / data.length;
    const chartHeight = chartContainer.height - 40;

    data.forEach((item, index) => {
      const barHeight = (item.amount / maxAmount) * chartHeight;
      const x = index * barWidth;
      const y = chartContainer.height - barHeight - 20;

      // Draw bar
      ctx.fillStyle = "#007bff";
      ctx.fillRect(x + 5, y, barWidth - 10, barHeight);

      // Draw hour label
      ctx.fillStyle = "#333";
      ctx.font = "12px Arial";
      ctx.textAlign = "center";
      ctx.fillText(item.hour, x + barWidth / 2, chartContainer.height - 5);
    });
  }
}

// Register the component
registry
  .category("dashboard_extensions")
  .add("dashboard_today", DashboardTodayExtension);

// CSS for styling
const todayCSS = `
.period-dropdown option[value="today"] {
    font-weight: bold;
    color: #007bff;
}

.today-metrics {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
}

.hourly-chart {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
`;

// Inject CSS
const style = document.createElement("style");
style.textContent = todayCSS;
document.head.appendChild(style);
