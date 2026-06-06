frappe.pages["sales-training-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales Training Dashboard"),
		single_column: true,
	});

	new SalesTrainingDashboard(page);
};

class SalesTrainingDashboard {
	constructor(page) {
		this.page = page;
		this.charts = {};
		this.apex_ready = false;
		this.active_sales_view = "pipeline";
		this.active_training_view = "course";
		this.make_filters();
		this.make_layout();
		this.bind_events();
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.load_apex();
	}

	make_filters() {
		this.from_date = this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -29),
			change: () => this.refresh(),
		});
		this.to_date = this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			change: () => this.refresh(),
		});
		this.customer = this.page.add_field({
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			change: () => this.refresh(),
		});
		this.course = this.page.add_field({
			fieldname: "course",
			label: __("Course"),
			fieldtype: "Link",
			options: "Course",
			change: () => this.refresh(),
		});
	}

	make_layout() {
		this.$root = $(`
			<div class="sales-training-dashboard">
				<div class="std-filter-strip">
					<div>
						<div class="std-strip-title">${__("Sales and Training Overview")}</div>
						<div class="std-strip-subtitle">${__("Click chart bars or table rows to filter by customer or course")}</div>
					</div>
					<div class="std-active-filters"></div>
				</div>
				<div class="std-kpi-grid">
					${this.kpi_card("total_sales_booked", __("Total Sales Booked"), __("Submitted Sales Orders"))}
					${this.kpi_card("pending_candidates", __("Candidates To Invoice"), __("Pending invoice creation"))}
					${this.kpi_card("tentative_invoice_value", __("Tentative Value"), __("Based on previous invoice value"))}
					${this.kpi_card("training_candidates", __("Training Candidates"), __("Candidates in training period"))}
				</div>
				<div class="std-chart-grid">
					<section class="std-panel">
						<div class="std-panel-head">
							<h3>${__("Sales Data")}</h3>
							<div class="std-segments" data-chart-group="sales">
								<button class="active" data-sales-view="pipeline">${__("Pipeline")}</button>
								<button data-sales-view="customer">${__("Customer")}</button>
								<button data-sales-view="pending">${__("Pending")}</button>
							</div>
						</div>
						<div id="std-sales-chart" class="std-chart"></div>
					</section>
					<section class="std-panel">
						<div class="std-panel-head">
							<h3>${__("Training Data")}</h3>
							<div class="std-segments" data-chart-group="training">
								<button class="active" data-training-view="course">${__("Course")}</button>
								<button data-training-view="customer">${__("Customer")}</button>
								<button data-training-view="status">${__("Status")}</button>
							</div>
						</div>
						<div id="std-course-chart" class="std-chart"></div>
					</section>
				</div>
				<section class="std-panel std-wide-panel">
					<div class="std-panel-head">
						<h3>${__("Sales Trend")}</h3>
						<span>${__("Daily sales orders in selected period")}</span>
					</div>
					<div id="std-trend-chart" class="std-chart std-chart-short"></div>
				</section>
				<section class="std-panel std-wide-panel">
					<div class="std-panel-head">
						<h3>${__("Invoice Queue")}</h3>
						<span>${__("Top pending customer and course combinations")}</span>
					</div>
					<div class="std-table-wrap">
						<table class="table table-bordered std-table">
							<thead>
								<tr>
									<th>${__("Customer")}</th>
									<th>${__("Course")}</th>
									<th class="text-right">${__("Candidates")}</th>
									<th class="text-right">${__("Avg Previous Value")}</th>
									<th class="text-right">${__("Tentative Value")}</th>
								</tr>
							</thead>
							<tbody class="std-breakdown-body"></tbody>
						</table>
					</div>
				</section>
			</div>
		`).appendTo(this.page.body);

		this.add_styles();
	}

	bind_events() {
		this.$root.on("click", "[data-sales-view]", (event) => {
			this.active_sales_view = $(event.currentTarget).data("salesView");
			this.$root.find("[data-sales-view]").removeClass("active");
			$(event.currentTarget).addClass("active");
			this.render_sales_chart();
		});

		this.$root.on("click", "[data-training-view]", (event) => {
			this.active_training_view = $(event.currentTarget).data("trainingView");
			this.$root.find("[data-training-view]").removeClass("active");
			$(event.currentTarget).addClass("active");
			this.render_course_chart();
		});

		this.$root.on("click", "[data-filter-customer]", (event) => {
			const value = $(event.currentTarget).data("filterCustomer");
			if (value && value !== "No Customer") {
				this.customer.set_value(value);
			}
		});

		this.$root.on("click", "[data-filter-course]", (event) => {
			const value = $(event.currentTarget).data("filterCourse");
			if (value && value !== "No Course") {
				this.course.set_value(value);
			}
		});

		this.$root.on("click", ".std-clear-filter", (event) => {
			const fieldname = $(event.currentTarget).data("fieldname");
			if (fieldname === "customer") this.customer.set_value("");
			if (fieldname === "course") this.course.set_value("");
		});
	}

	kpi_card(fieldname, label, note) {
		return `
			<div class="std-kpi" data-kpi="${fieldname}">
				<div class="std-kpi-label">${label}</div>
				<div class="std-kpi-value">0</div>
				<div class="std-kpi-note">${note}</div>
			</div>
		`;
	}

	get_filters() {
		return {
			from_date: this.from_date.get_value(),
			to_date: this.to_date.get_value(),
			customer: this.customer.get_value(),
			course: this.course.get_value(),
		};
	}

	load_apex() {
		if (window.ApexCharts) {
			this.apex_ready = true;
			this.refresh();
			return;
		}

		frappe.require(["https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.js"], () => {
			this.apex_ready = !!window.ApexCharts;
			this.refresh();
		});
	}

	refresh() {
		this.$root.addClass("is-loading");
		frappe.call({
			method: "numerouno.numerouno.page.sales_training_dashboard.sales_training_dashboard.get_dashboard_data",
			args: { filters: this.get_filters() },
			callback: (response) => {
				this.data = response.message || {};
				this.render();
			},
			error: () => {
				frappe.show_alert({ message: __("Unable to load dashboard data"), indicator: "red" });
			},
			always: () => {
				this.$root.removeClass("is-loading");
			},
		});
	}

	render() {
		const kpis = this.data.kpis || {};
		this.set_kpi("total_sales_booked", this.format_currency(kpis.total_sales_booked), `${kpis.sales_orders || 0} ${__("sales orders")}`);
		this.set_kpi("pending_candidates", this.format_number(kpis.pending_candidates), __("Candidates ready for invoice review"));
		this.set_kpi("tentative_invoice_value", this.format_currency(kpis.tentative_invoice_value), `${__("Avg")} ${this.format_currency(kpis.avg_previous_invoice_value)}`);
		this.set_kpi("training_candidates", this.format_number(kpis.training_candidates), `${this.format_number(kpis.training_groups)} ${__("groups")} / ${this.format_number(kpis.unique_candidates)} ${__("unique")}`);

		this.render_sales_chart();
		this.render_course_chart();
		this.render_trend_chart();
		this.render_breakdown();
		this.render_active_filters();
	}

	set_kpi(fieldname, value, note) {
		const $card = this.$root.find(`[data-kpi="${fieldname}"]`);
		$card.find(".std-kpi-value").text(value || 0);
		$card.find(".std-kpi-note").text(note || "");
	}

	render_sales_chart() {
		const charts = this.data.charts || {};
		const chart = this.active_sales_view === "customer"
			? charts.sales_by_customer || { labels: [], values: [] }
			: this.active_sales_view === "pending"
				? charts.pending_by_customer || { labels: [], values: [] }
				: charts.sales_vs_tentative || { labels: [], values: [] };
		const is_customer_chart = ["customer", "pending"].includes(this.active_sales_view);
		const labels = is_customer_chart
			? (chart.labels || []).map((label) => this.short_label(label, 30))
			: chart.labels || [];
		const title = this.active_sales_view === "pending" ? __("Pending Candidates") : __("Amount");

		this.make_chart("sales", "#std-sales-chart", {
			chart: { type: "bar", height: 285, toolbar: { show: false } },
			series: [{ name: title, data: chart.values || [] }],
			xaxis: {
				categories: labels,
				labels: { style: { colors: "#4f5f76", fontSize: "12px" } },
			},
			yaxis: {
				labels: {
					formatter: (value) => this.active_sales_view === "pending" ? this.format_number(value) : this.short_currency(value),
				},
			},
			colors: [this.active_sales_view === "pending" ? "#f59e0b" : "#2563eb"],
			plotOptions: {
				bar: {
					borderRadius: 7,
					columnWidth: is_customer_chart ? "55%" : "42%",
					horizontal: is_customer_chart,
					barHeight: "56%",
				},
			},
			dataLabels: {
				enabled: this.active_sales_view === "pending",
				style: { colors: ["#253244"] },
				offsetX: 8,
			},
			grid: { borderColor: "#edf1f7" },
			tooltip: {
				x: { formatter: (_value, opts) => chart.labels?.[opts.dataPointIndex] || "" },
				y: {
					formatter: (value) => this.active_sales_view === "pending" ? this.format_number(value) : this.format_currency(value),
				},
			},
		}, {
			labels: chart.labels || [],
			filter: is_customer_chart ? "customer" : null,
		});
	}

	render_course_chart() {
		const charts = this.data.charts || {};
		if (this.active_training_view === "status") {
			this.render_status_chart();
			return;
		}

		const chart = this.active_training_view === "customer"
			? charts.training_by_customer || { labels: [], candidates: [], groups: [] }
			: charts.course_candidates || { labels: [], values: [] };
		const labels = (chart.labels || []).map((label) => this.short_label(label, 34));
		const series = this.active_training_view === "customer"
			? [
					{ name: __("Candidates"), data: chart.candidates || [] },
					{ name: __("Groups"), data: chart.groups || [] },
				]
			: [{ name: __("Candidates"), data: chart.values?.length ? chart.values : [0] }];

		this.make_chart("course", "#std-course-chart", {
			chart: { type: "bar", height: 285, toolbar: { show: false } },
			series,
			xaxis: {
				categories: labels.length ? labels : [__("No Data")],
				labels: { style: { colors: "#4f5f76", fontSize: "12px" } },
			},
			colors: this.active_training_view === "customer" ? ["#16a085", "#2563eb"] : ["#16a085"],
			plotOptions: { bar: { borderRadius: 6, horizontal: true, barHeight: "56%" } },
			dataLabels: { enabled: true, style: { colors: ["#253244"] }, offsetX: 8 },
			grid: { borderColor: "#edf1f7" },
			tooltip: {
				x: { formatter: (_value, opts) => chart.labels?.[opts.dataPointIndex] || "" },
				y: { formatter: (value) => this.format_number(value) },
			},
			legend: { show: this.active_training_view === "customer", position: "top" },
		}, {
			labels: chart.labels || [],
			filter: this.active_training_view === "customer" ? "customer" : "course",
		});
	}

	render_status_chart() {
		const chart = this.data.charts?.invoice_status_mix || { labels: [], values: [] };
		this.make_chart("course", "#std-course-chart", {
			chart: { type: "donut", height: 285, toolbar: { show: false } },
			series: chart.values || [],
			labels: chart.labels || [],
			colors: ["#f59e0b", "#2563eb", "#16a085"],
			dataLabels: { enabled: true },
			plotOptions: { pie: { donut: { size: "68%" } } },
			tooltip: { y: { formatter: (value) => `${this.format_number(value)} ${__("candidates")}` } },
			legend: { show: true, position: "bottom" },
		});
	}

	render_trend_chart() {
		const chart = this.data.charts?.sales_trend || { labels: [], values: [] };
		this.make_chart("trend", "#std-trend-chart", {
			chart: { type: "area", height: 235, toolbar: { show: false }, zoom: { enabled: false } },
			series: [{ name: __("Sales Booked"), data: chart.values || [] }],
			xaxis: {
				categories: chart.labels || [],
				tickAmount: 8,
				labels: { rotate: 0, style: { colors: "#4f5f76", fontSize: "11px" } },
			},
			yaxis: { labels: { formatter: (value) => this.short_currency(value) } },
			colors: ["#7c3aed"],
			stroke: { width: 2.5, curve: "smooth" },
			fill: {
				type: "gradient",
				gradient: { shadeIntensity: 1, opacityFrom: 0.28, opacityTo: 0.03, stops: [0, 90, 100] },
			},
			dataLabels: { enabled: false },
			grid: { borderColor: "#edf1f7" },
			tooltip: { y: { formatter: (value) => this.format_currency(value) } },
		});
	}

	make_chart(name, selector, options, interaction = {}) {
		const element = this.$root.find(selector).get(0);
		if (!element) return;

		if (!this.apex_ready || !window.ApexCharts) {
			element.innerHTML = `<div class="std-empty">${__("Chart library is loading")}</div>`;
			return;
		}

		if (this.charts[name]) {
			this.charts[name].destroy();
		}

		const series = options.series || [];
		const has_data = series.some((item) => {
			if (typeof item === "number") return flt(item) !== 0;
			return (item.data || []).some((value) => flt(value) !== 0);
		});
		element.innerHTML = "";
		if (!has_data) {
			element.innerHTML = `<div class="std-empty">${__("No chart data for this range")}</div>`;
			return;
		}

		this.charts[name] = new ApexCharts(element, {
			...options,
			legend: options.legend || { show: false },
			chart: {
				...(options.chart || {}),
				events: {
					dataPointSelection: (_event, _chartContext, config) => {
						const label = interaction.labels?.[config.dataPointIndex];
						this.apply_chart_filter(interaction.filter, label);
					},
				},
			},
		});
		this.charts[name].render();
	}

	apply_chart_filter(type, value) {
		if (!type || !value || ["No Customer", "No Course"].includes(value)) return;
		if (type === "customer") this.customer.set_value(value);
		if (type === "course") this.course.set_value(value);
	}

	render_breakdown() {
		const rows = this.data.pending_breakdown || [];
		const html = rows.length
			? rows
					.map(
						(row) => `
							<tr>
								<td><button class="std-link-button" data-filter-customer="${frappe.utils.escape_html(row.customer || "")}">${frappe.utils.escape_html(row.customer || "")}</button></td>
								<td><button class="std-link-button" data-filter-course="${frappe.utils.escape_html(row.course || "")}">${frappe.utils.escape_html(row.course || "")}</button></td>
								<td class="text-right">${this.format_number(row.pending_candidates)}</td>
								<td class="text-right">${this.format_currency(row.avg_candidate_value)}</td>
								<td class="text-right">${this.format_currency(row.tentative_value)}</td>
							</tr>
						`
					)
					.join("")
			: `<tr><td colspan="5" class="text-muted text-center">${__("No pending candidates found")}</td></tr>`;

		this.$root.find(".std-breakdown-body").html(html);
	}

	render_active_filters() {
		const active = [];
		if (this.customer.get_value()) {
			active.push({ fieldname: "customer", label: __("Customer"), value: this.customer.get_value() });
		}
		if (this.course.get_value()) {
			active.push({ fieldname: "course", label: __("Course"), value: this.course.get_value() });
		}

		const html = active.length
			? active
					.map(
						(item) => `
							<span class="std-filter-pill">
								<strong>${item.label}</strong>
								${frappe.utils.escape_html(item.value)}
								<button class="std-clear-filter" data-fieldname="${item.fieldname}" type="button">x</button>
							</span>
						`
					)
					.join("")
			: `<span class="std-filter-hint">${__("No customer/course filter applied")}</span>`;

		this.$root.find(".std-active-filters").html(html);
	}

	format_currency(value) {
		const currency = frappe.defaults.get_default("currency") || "AED";
		if (frappe.utils?.format_currency) {
			return frappe.utils.format_currency(flt(value || 0, 2), currency);
		}
		return `${currency} ${this.format_number(flt(value || 0, 2), 2)}`;
	}

	format_number(value, decimals = 0) {
		return flt(value || 0, decimals).toLocaleString(undefined, {
			minimumFractionDigits: decimals,
			maximumFractionDigits: decimals,
		});
	}

	short_currency(value) {
		const amount = flt(value || 0);
		if (Math.abs(amount) >= 1000000) return `${(amount / 1000000).toFixed(1)}M`;
		if (Math.abs(amount) >= 1000) return `${(amount / 1000).toFixed(0)}K`;
		return this.format_number(amount);
	}

	short_label(label, max_length) {
		if (!label) return __("No Course");
		return label.length > max_length ? `${label.slice(0, max_length - 1)}...` : label;
	}

	add_styles() {
		if (document.getElementById("sales-training-dashboard-style")) return;

		$(`<style id="sales-training-dashboard-style">
			.sales-training-dashboard {
				--std-border: #d8dee8;
				--std-soft: #f8fafc;
				--std-text: #253244;
				--std-muted: #667085;
				--std-blue: #2563eb;
				--std-green: #16a085;
				--std-violet: #7c3aed;
				padding-bottom: 24px;
			}
			.std-filter-strip {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 16px;
				padding: 12px 14px;
				margin-bottom: 12px;
				border: 1px solid var(--std-border);
				border-radius: 8px;
				background: #fff;
			}
			.std-strip-title {
				font-weight: 750;
				color: var(--std-text);
			}
			.std-strip-subtitle {
				margin-top: 2px;
				font-size: 12px;
				color: var(--std-muted);
			}
			.std-active-filters {
				display: flex;
				align-items: center;
				justify-content: flex-end;
				flex-wrap: wrap;
				gap: 8px;
			}
			.std-filter-pill {
				display: inline-flex;
				align-items: center;
				gap: 7px;
				max-width: 360px;
				padding: 5px 8px;
				border: 1px solid #c7d2fe;
				border-radius: 999px;
				background: #eef2ff;
				color: #1e3a8a;
				font-size: 12px;
			}
			.std-filter-pill strong { color: #1d4ed8; }
			.std-filter-pill button {
				border: 0;
				background: transparent;
				color: #1e3a8a;
				font-weight: 700;
				line-height: 1;
			}
			.std-filter-hint {
				color: var(--std-muted);
				font-size: 12px;
			}
			.std-kpi-grid {
				display: grid;
				grid-template-columns: repeat(4, minmax(180px, 1fr));
				gap: 12px;
				margin-bottom: 12px;
			}
			.std-kpi {
				min-height: 116px;
				padding: 16px;
				border: 1px solid var(--std-border);
				border-radius: 8px;
				background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%);
				box-shadow: 0 1px 2px rgba(16, 24, 40, .05);
			}
			.std-kpi:nth-child(1) { border-top: 3px solid var(--std-blue); }
			.std-kpi:nth-child(2) { border-top: 3px solid #f59e0b; }
			.std-kpi:nth-child(3) { border-top: 3px solid var(--std-violet); }
			.std-kpi:nth-child(4) { border-top: 3px solid var(--std-green); }
			.std-kpi-label {
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0;
				color: var(--std-muted);
			}
			.std-kpi-value {
				margin-top: 12px;
				font-size: 24px;
				line-height: 1.15;
				font-weight: 750;
				color: var(--std-text);
				overflow-wrap: anywhere;
			}
			.std-kpi-note {
				margin-top: 8px;
				font-size: 12px;
				color: var(--std-muted);
			}
			.std-chart-grid {
				display: grid;
				grid-template-columns: repeat(2, minmax(260px, 1fr));
				gap: 12px;
				margin-bottom: 12px;
			}
			.std-panel {
				border: 1px solid var(--std-border);
				border-radius: 8px;
				background: #fff;
				box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
				overflow: hidden;
			}
			.std-wide-panel { margin-bottom: 12px; }
			.std-panel-head {
				display: flex;
				justify-content: space-between;
				gap: 12px;
				align-items: center;
				min-height: 48px;
				padding: 10px 14px;
				border-bottom: 1px solid var(--std-border);
				background: var(--std-soft);
			}
			.std-panel-head h3 {
				margin: 0;
				font-size: 15px;
				font-weight: 700;
				color: var(--std-text);
			}
			.std-panel-head span {
				font-size: 12px;
				color: var(--std-muted);
				text-align: right;
			}
			.std-segments {
				display: inline-flex;
				align-items: center;
				padding: 2px;
				border: 1px solid var(--std-border);
				border-radius: 8px;
				background: #fff;
			}
			.std-segments button {
				border: 0;
				border-radius: 6px;
				background: transparent;
				color: #4f5f76;
				font-size: 12px;
				font-weight: 650;
				padding: 5px 9px;
			}
			.std-segments button.active {
				background: #253244;
				color: #fff;
			}
			.std-chart {
				min-height: 285px;
				padding: 8px 12px 4px;
			}
			.std-chart-short { min-height: 235px; }
			.std-empty {
				min-height: 180px;
				display: flex;
				align-items: center;
				justify-content: center;
				color: var(--std-muted);
				font-size: 13px;
			}
			.std-table-wrap {
				overflow: auto;
				padding: 12px;
			}
			.std-table {
				margin-bottom: 0;
				background: #fff;
			}
			.std-table th {
				background: #f8fafc;
				font-size: 12px;
				color: #4f5f76;
				white-space: nowrap;
			}
			.std-table td {
				vertical-align: middle;
			}
			.std-link-button {
				border: 0;
				background: transparent;
				color: #1d4ed8;
				padding: 0;
				text-align: left;
				font-weight: 500;
			}
			.std-link-button:hover {
				text-decoration: underline;
			}
			.sales-training-dashboard.is-loading {
				opacity: .65;
				pointer-events: none;
			}
			@media (max-width: 1100px) {
				.std-kpi-grid,
				.std-chart-grid {
					grid-template-columns: repeat(2, minmax(180px, 1fr));
				}
			}
			@media (max-width: 700px) {
				.std-kpi-grid,
				.std-chart-grid {
					grid-template-columns: 1fr;
				}
				.std-panel-head {
					align-items: flex-start;
					flex-direction: column;
				}
				.std-panel-head span { text-align: left; }
				.std-filter-strip {
					align-items: flex-start;
					flex-direction: column;
				}
				.std-active-filters {
					justify-content: flex-start;
				}
			}
		</style>`).appendTo("head");
	}
}
