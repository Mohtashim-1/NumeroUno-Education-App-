frappe.pages["management-dashboard"].on_page_load = function (wrapper) {
	new ManagementDashboard(wrapper);
};

class ManagementDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Management Dashboard",
			single_column: true,
		});
		this.charts = {};
		this.filters = {};
		this.apexReady = false;

		this.page.main.html(this.get_template());
		this.$root = $(this.page.main).find(".management-dashboard-page");
		this.$kpis = this.$root.find('[data-region="kpis"]');
		this.$highlights = this.$root.find('[data-region="highlights"]');
		this.$courseTable = this.$root.find('[data-region="course-table"]');
		this.$customerTable = this.$root.find('[data-region="customer-table"]');
		this.$supplierTable = this.$root.find('[data-region="supplier-table"]');
		this.$instructorTable = this.$root.find('[data-region="instructor-table"]');
		this.$companyTable = this.$root.find('[data-region="company-table"]');
		this.$transactionsTable = this.$root.find('[data-region="transactions-table"]');
		this.$recentGroupsTable = this.$root.find('[data-region="recent-groups-table"]');
		this.$summaryBlock = this.$root.find('[data-region="summary-block"]');
		this.$links = this.$root.find('[data-region="report-links"]');
		this.$rangeLabel = this.$root.find('[data-region="range-label"]');

		this.make_filters();
		this.bind_actions();
		this.load_apex();
	}

	get_template() {
		return `
			<div class="management-dashboard-page">
				<section class="hero">
					<div class="hero-copy">
						<h2>Management Dashboard</h2>
						<p>Periodic sales, collections, expenses, and training intelligence for management review.</p>
					</div>
					<div class="hero-chip" data-region="range-label">Loading current range</div>
				</section>

				<section class="filters-panel">
					<div class="filters-grid" data-region="filters"></div>
				</section>

				<section class="panel" style="margin-bottom: 18px;">
					<div class="panel-head">
						<div>
							<h3>Executive Summary</h3>
							<div class="section-note">Compact business readout for the selected period.</div>
						</div>
					</div>
					<div data-region="summary-block"></div>
				</section>

				<section class="kpi-grid" data-region="kpis"></section>

				<section class="mini-grid" data-region="highlights"></section>

				<section class="chart-grid">
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Financial Trend</h3>
								<div class="section-note">Sales, receipts, and purchases over the selected period.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-financial-trend"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Revenue Mix</h3>
								<div class="section-note">Current-period commercial composition.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-revenue-mix"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Top Customers</h3>
								<div class="section-note">Sales concentration by customer.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-top-customers"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Customer Share</h3>
								<div class="section-note">Contribution mix across the top customers.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-customer-share"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Surplus Trend</h3>
								<div class="section-note">Sales less purchases over the selected timeline.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-surplus-trend"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Cash Position Trend</h3>
								<div class="section-note">Collections against expenses with net operational cash.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-cash-position"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Training Candidate Trend</h3>
								<div class="section-note">Candidate intake across scheduled groups.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-training-trend"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Training Group Trend</h3>
								<div class="section-note">How many groups started in each selected period.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-training-groups-trend"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Instructor Performance</h3>
								<div class="section-note">Groups and candidates handled by instructor.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-training-instructor"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Company Training Report</h3>
								<div class="section-note">Corporate and direct-training distribution.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-training-company"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Course Mix</h3>
								<div class="section-note">Training volume split by course.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-training-course"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Top Suppliers</h3>
								<div class="section-note">Largest purchase exposure by supplier.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-top-suppliers"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Document Volume</h3>
								<div class="section-note">Transaction counts across finance and training.</div>
							</div>
						</div>
						<div class="chart-slot" id="management-document-volume"></div>
					</div>
				</section>

				<section class="footer-grid" style="margin-top: 16px;">
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Training by Course</h3>
								<div class="section-note">Core course breakdown with group and candidate counts.</div>
							</div>
						</div>
						<div data-region="course-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Top Customers Detail</h3>
								<div class="section-note">Amount and invoice count per customer.</div>
							</div>
						</div>
						<div data-region="customer-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Top Suppliers Detail</h3>
								<div class="section-note">Purchase concentration and invoice counts.</div>
							</div>
						</div>
						<div data-region="supplier-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Instructor Detail</h3>
								<div class="section-note">Groups and candidate load by instructor.</div>
							</div>
						</div>
						<div data-region="instructor-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Company Detail</h3>
								<div class="section-note">Training volumes by company or direct client.</div>
							</div>
						</div>
						<div data-region="company-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Recent Transactions</h3>
								<div class="section-note">Latest sales, receipts, and purchase documents in range.</div>
							</div>
						</div>
						<div data-region="transactions-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Recent Training Groups</h3>
								<div class="section-note">Latest course batches with company, instructor, and candidate load.</div>
							</div>
						</div>
						<div data-region="recent-groups-table"></div>
					</div>
					<div class="panel">
						<div class="panel-head">
							<div>
								<h3>Detailed Reports</h3>
								<div class="section-note">Open operational reports behind the dashboard numbers.</div>
							</div>
						</div>
						<div class="report-links" data-region="report-links"></div>
					</div>
				</section>
			</div>
		`;
	}

	make_filters() {
		const $target = this.$root.find('[data-region="filters"]');
		const fields = [
			{ fieldtype: "Date", fieldname: "from_date", label: "From Date", default: frappe.datetime.add_months(frappe.datetime.get_today(), -6) },
			{ fieldtype: "Date", fieldname: "to_date", label: "To Date", default: frappe.datetime.get_today() },
			{
				fieldtype: "Select",
				fieldname: "period",
				label: "Period",
				options: ["Daily", "Weekly", "Monthly", "Quarterly"],
				default: "Monthly",
			},
			{ fieldtype: "Link", fieldname: "company", label: "Company", options: "Company" },
			{ fieldtype: "Link", fieldname: "customer", label: "Customer", options: "Customer" },
			{ fieldtype: "Link", fieldname: "program", label: "Program", options: "Program" },
			{ fieldtype: "Link", fieldname: "course", label: "Course", options: "Course" },
		];

		fields.forEach((df) => {
			const $field = $('<div class="filter-cell"></div>').appendTo($target);
			const control = frappe.ui.form.make_control({
				df,
				parent: $field,
				render_input: true,
			});
			control.refresh();
			control.set_value(df.default || "");
			this.filters[df.fieldname] = control;
		});

		const $actions = $('<div class="filter-actions"></div>').appendTo($target);
		this.applyButton = $('<button class="btn btn-primary">Apply</button>').appendTo($actions);
		this.resetButton = $('<button class="btn btn-default">Reset</button>').appendTo($actions);
	}

	bind_actions() {
		this.applyButton.on("click", () => this.refresh());
		this.resetButton.on("click", () => this.reset_filters());
		Object.values(this.filters).forEach((control) => {
			control.$input && control.$input.on("change", () => this.refresh());
		});
	}

	load_apex() {
		if (window.ApexCharts) {
			this.apexReady = true;
			this.refresh();
			return;
		}

		frappe.require(["https://cdn.jsdelivr.net/npm/apexcharts/dist/apexcharts.min.js"], () => {
			this.apexReady = !!window.ApexCharts;
			this.refresh();
		});
	}

	get_filter_values() {
		return Object.fromEntries(
			Object.entries(this.filters).map(([key, control]) => [key, control.get_value()])
		);
	}

	reset_filters() {
		this.filters.from_date.set_value(frappe.datetime.add_months(frappe.datetime.get_today(), -6));
		this.filters.to_date.set_value(frappe.datetime.get_today());
		this.filters.period.set_value("Monthly");
		["company", "customer", "program", "course"].forEach((fieldname) => this.filters[fieldname].set_value(""));
		this.refresh();
	}

	refresh() {
		if (!this.apexReady) {
			return;
		}

		frappe.call({
			method: "numerouno.numerouno.page.management_dashboard.management_dashboard.get_management_dashboard_data",
			args: {
				filters: this.get_filter_values(),
			},
			freeze: false,
			callback: (r) => {
				if (!r.message) {
					return;
				}
				this.render(r.message);
			},
			error: () => {
				frappe.show_alert({ message: __("Unable to load dashboard data"), indicator: "red" });
			},
		});
	}

	render(data) {
		this.$rangeLabel.text(`${frappe.datetime.str_to_user(data.filters.from_date)} to ${frappe.datetime.str_to_user(data.filters.to_date)} · ${data.filters.period}`);
		this.render_summary(data.summary, data.highlights);
		this.render_kpis(data.kpis);
		this.render_highlights(data.highlights);
		this.render_course_table(data.tables.course_breakdown || []);
		this.render_rank_table(this.$customerTable, data.tables.customer_breakdown || [], "Customer");
		this.render_rank_table(this.$supplierTable, data.tables.supplier_breakdown || [], "Supplier");
		this.render_training_table(this.$instructorTable, data.tables.instructor_breakdown || [], "Instructor");
		this.render_training_table(this.$companyTable, data.tables.company_breakdown || [], "Company");
		this.render_transactions_table(data.tables.recent_transactions || []);
		this.render_recent_groups(data.tables.recent_training_groups || []);
		this.render_links(data.report_links || []);
		this.render_charts(data.charts);
	}

	render_summary(summary, highlights) {
		const topPeriod = summary?.top_period
			? `<strong>${frappe.utils.escape_html(summary.top_period.label)}</strong> at ${format_currency(summary.top_period.value)} sales`
			: "No sales peak identified for this range";
		this.$summaryBlock.html(`
			<div class="mini-grid">
				<div class="mini-card">
					<div class="mini-label">Best Sales Period</div>
					<div class="mini-value" style="font-size:18px;">${topPeriod}</div>
				</div>
				<div class="mini-card">
					<div class="mini-label">Net Position</div>
					<div class="mini-value">${format_currency(summary?.net_position || 0)}</div>
				</div>
				<div class="mini-card">
					<div class="mini-label">Candidates Per Group</div>
					<div class="mini-value">${format_number(summary?.candidate_per_group || 0, null, 2)}</div>
				</div>
				<div class="mini-card">
					<div class="mini-label">Document Load</div>
					<div class="mini-value">${highlights.sales_docs + highlights.receipt_docs + highlights.expense_docs}</div>
				</div>
			</div>
		`);
	}

	render_kpis(kpis) {
		this.$kpis.empty();
		kpis.forEach((kpi) => {
			const changeClass = kpi.change > 0 ? "positive" : kpi.change < 0 ? "negative" : "neutral";
			const changeSign = kpi.change > 0 ? "+" : "";
			$(`
				<div class="panel kpi-card">
					<div class="kpi-label">${frappe.utils.escape_html(kpi.label)}</div>
					<div class="kpi-value">${this.format_value(kpi.value, kpi.label)}</div>
					<div class="kpi-change ${changeClass}">${changeSign}${format_number(kpi.change, null, 2)}%</div>
					<div class="kpi-subtitle">${frappe.utils.escape_html(kpi.subtitle)}</div>
				</div>
			`).appendTo(this.$kpis);
		});
	}

	render_highlights(highlights) {
		this.$highlights.empty();
		const cards = [
			{ label: "Gross Surplus", value: format_currency(highlights.gross_surplus) },
			{ label: "Collection Gap", value: format_currency(highlights.collection_gap) },
			{ label: "Collection Efficiency", value: `${format_number(highlights.collection_efficiency, null, 2)}%` },
			{ label: "Expense Ratio", value: `${format_number(highlights.expense_ratio, null, 2)}%` },
			{ label: "Avg Invoice", value: format_currency(highlights.avg_invoice_value) },
			{ label: "Avg Receipt", value: format_currency(highlights.avg_receipt_value) },
			{ label: "Training Groups", value: highlights.training_groups },
			{ label: "Active Instructors", value: highlights.instructors },
			{ label: "Training Companies", value: highlights.companies },
		];

		cards.forEach((card) => {
			$(`
				<div class="mini-card">
					<div class="mini-label">${frappe.utils.escape_html(card.label)}</div>
					<div class="mini-value">${card.value}</div>
				</div>
			`).appendTo(this.$highlights);
		});
	}

	render_course_table(rows) {
		if (!rows.length) {
			this.$courseTable.html('<div class="empty-state">No training rows found for the selected filters.</div>');
			return;
		}

		const body = rows
			.map(
				(row) => `
					<tr>
						<td>${frappe.utils.escape_html(row.label || "")}</td>
						<td>${row.groups_count || 0}</td>
						<td>${row.candidates_count || 0}</td>
					</tr>
				`
			)
			.join("");

		this.$courseTable.html(`
			<table class="course-table">
				<thead>
					<tr>
						<th>Course</th>
						<th>Groups</th>
						<th>Candidates</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_rank_table($target, rows, label) {
		if (!rows.length) {
			$target.html('<div class="empty-state">No detail rows found for this range.</div>');
			return;
		}

		const body = rows
			.map(
				(row) => `
					<tr>
						<td>${frappe.utils.escape_html(row.label || "")}</td>
						<td>${row.count || 0}</td>
						<td>${format_currency(row.amount || 0)}</td>
					</tr>
				`
			)
			.join("");

		$target.html(`
			<table class="course-table">
				<thead>
					<tr>
						<th>${label}</th>
						<th>Docs</th>
						<th>Amount</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_training_table($target, rows, label) {
		if (!rows.length) {
			$target.html('<div class="empty-state">No training detail rows found for this range.</div>');
			return;
		}

		const body = rows
			.map(
				(row) => `
					<tr>
						<td>${frappe.utils.escape_html(row.label || "")}</td>
						<td>${row.groups_count || 0}</td>
						<td>${row.candidates_count || 0}</td>
					</tr>
				`
			)
			.join("");

		$target.html(`
			<table class="course-table">
				<thead>
					<tr>
						<th>${label}</th>
						<th>Groups</th>
						<th>Candidates</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_transactions_table(rows) {
		if (!rows.length) {
			this.$transactionsTable.html('<div class="empty-state">No recent transactions found for this range.</div>');
			return;
		}

		const body = rows
			.map(
				(row) => `
					<tr>
						<td>${frappe.datetime.str_to_user(row.date)}</td>
						<td>${frappe.utils.escape_html(row.type || "")}</td>
						<td>${frappe.utils.escape_html(row.party || "")}</td>
						<td>${frappe.utils.escape_html(row.reference || "")}</td>
						<td>${format_currency(row.amount || 0)}</td>
					</tr>
				`
			)
			.join("");

		this.$transactionsTable.html(`
			<table class="course-table">
				<thead>
					<tr>
						<th>Date</th>
						<th>Type</th>
						<th>Party</th>
						<th>Reference</th>
						<th>Amount</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_recent_groups(rows) {
		if (!rows.length) {
			this.$recentGroupsTable.html('<div class="empty-state">No recent training groups found for this range.</div>');
			return;
		}

		const body = rows
			.map(
				(row) => `
					<tr>
						<td>${frappe.datetime.str_to_user(row.from_date)}</td>
						<td>${frappe.utils.escape_html(row.course || "")}</td>
						<td>${frappe.utils.escape_html(row.company || "")}</td>
						<td>${frappe.utils.escape_html(row.instructors || "")}</td>
						<td>${row.candidates || 0}</td>
					</tr>
				`
			)
			.join("");

		this.$recentGroupsTable.html(`
			<table class="course-table">
				<thead>
					<tr>
						<th>Start</th>
						<th>Course</th>
						<th>Company</th>
						<th>Instructor</th>
						<th>Candidates</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_links(links) {
		this.$links.empty();
		links.forEach((link) => {
			$(`<a class="report-link" href="${link.route}"><span>${frappe.utils.escape_html(link.label)}</span><i class="fa fa-arrow-right"></i></a>`).appendTo(this.$links);
		});
	}

	render_charts(charts) {
		this.draw_chart("management-financial-trend", {
			chart: { type: "line", height: 320, toolbar: { show: false } },
			stroke: { width: [3, 3, 3], curve: "smooth" },
			series: [
				{ name: "Sales", data: charts.financial_trend.sales },
				{ name: "Collections", data: charts.financial_trend.collections },
				{ name: "Expenses", data: charts.financial_trend.expenses },
			],
			xaxis: { categories: charts.financial_trend.labels },
			colors: ["#0f7b6c", "#1f5eff", "#d96c2f"],
			yaxis: { labels: { formatter: (value) => this.short_currency(value) } },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
			legend: { position: "top" },
			grid: { borderColor: "#e1e8ef" },
		});

		this.draw_chart("management-surplus-trend", {
			chart: { type: "bar", height: 320, toolbar: { show: false } },
			series: [{ name: "Surplus", data: charts.financial_trend.surplus }],
			xaxis: { categories: charts.financial_trend.labels },
			colors: ["#0f7b6c"],
			plotOptions: { bar: { borderRadius: 6, columnWidth: "55%" } },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
		});

		this.draw_chart("management-revenue-mix", {
			chart: { type: "donut", height: 320 },
			series: charts.revenue_mix.values,
			labels: charts.revenue_mix.labels,
			colors: ["#0f7b6c", "#1f5eff", "#d96c2f"],
			legend: { position: "bottom" },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
			dataLabels: { enabled: true, formatter: (value) => `${value.toFixed(0)}%` },
		});

		this.draw_chart("management-top-customers", {
			chart: { type: "bar", height: 320, toolbar: { show: false } },
			series: [{ name: "Sales", data: charts.top_customers.values }],
			xaxis: { categories: charts.top_customers.labels },
			colors: ["#112033"],
			plotOptions: { bar: { borderRadius: 6, horizontal: true } },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
		});

		this.draw_chart("management-customer-share", {
			chart: { type: "donut", height: 320 },
			series: charts.customer_share.values,
			labels: charts.customer_share.labels,
			colors: ["#0f7b6c", "#1f5eff", "#d96c2f", "#112033", "#4f46e5", "#c2410c"],
			legend: { position: "bottom" },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
		});

		this.draw_chart("management-cash-position", {
			chart: { type: "line", height: 320, toolbar: { show: false } },
			series: [
				{ name: "Collections", data: charts.cash_position_trend.collections },
				{ name: "Expenses", data: charts.cash_position_trend.expenses },
				{ name: "Net Cash", data: charts.cash_position_trend.net },
			],
			xaxis: { categories: charts.cash_position_trend.labels },
			colors: ["#1f5eff", "#d96c2f", "#0f7b6c"],
			stroke: { width: [3, 3, 4], curve: "smooth" },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
			legend: { position: "top" },
		});

		this.draw_chart("management-training-trend", {
			chart: { type: "area", height: 320, toolbar: { show: false } },
			series: [{ name: "Candidates", data: charts.training_candidate_trend.values }],
			xaxis: { categories: charts.training_candidate_trend.labels },
			colors: ["#d96c2f"],
			fill: { type: "gradient", gradient: { shadeIntensity: 0.2, opacityFrom: 0.5, opacityTo: 0.08 } },
			dataLabels: { enabled: false },
			stroke: { curve: "smooth", width: 3 },
		});

		this.draw_chart("management-training-groups-trend", {
			chart: { type: "bar", height: 320, toolbar: { show: false } },
			series: [{ name: "Groups", data: charts.training_group_trend.values }],
			xaxis: { categories: charts.training_group_trend.labels },
			colors: ["#112033"],
			plotOptions: { bar: { borderRadius: 6, columnWidth: "50%" } },
			dataLabels: { enabled: true },
		});

		this.draw_chart("management-training-instructor", {
			chart: { type: "bar", height: 320, stacked: false, toolbar: { show: false } },
			series: [
				{ name: "Groups", data: charts.training_by_instructor.groups },
				{ name: "Candidates", data: charts.training_by_instructor.candidates },
			],
			xaxis: { categories: charts.training_by_instructor.labels },
			colors: ["#0f7b6c", "#d96c2f"],
			plotOptions: { bar: { borderRadius: 6, columnWidth: "52%" } },
			legend: { position: "top" },
		});

		this.draw_chart("management-training-company", {
			chart: { type: "bar", height: 320, stacked: true, toolbar: { show: false } },
			series: [
				{ name: "Groups", data: charts.training_by_company.groups },
				{ name: "Candidates", data: charts.training_by_company.candidates },
			],
			xaxis: { categories: charts.training_by_company.labels },
			colors: ["#1f5eff", "#0f7b6c"],
			plotOptions: { bar: { borderRadius: 6, columnWidth: "55%" } },
			legend: { position: "top" },
		});

		this.draw_chart("management-training-course", {
			chart: { type: "bar", height: 320, stacked: false, toolbar: { show: false } },
			series: [
				{ name: "Groups", data: charts.training_by_course.groups },
				{ name: "Candidates", data: charts.training_by_course.candidates },
			],
			xaxis: { categories: charts.training_by_course.labels },
			colors: ["#1f5eff", "#d96c2f"],
			plotOptions: { bar: { borderRadius: 6, horizontal: true, barHeight: "55%" } },
			legend: { position: "top" },
		});

		this.draw_chart("management-top-suppliers", {
			chart: { type: "bar", height: 320, toolbar: { show: false } },
			series: [{ name: "Purchases", data: charts.top_suppliers.values }],
			xaxis: { categories: charts.top_suppliers.labels },
			colors: ["#d96c2f"],
			plotOptions: { bar: { borderRadius: 6, horizontal: true } },
			tooltip: { y: { formatter: (value) => format_currency(value) } },
		});

		this.draw_chart("management-document-volume", {
			chart: { type: "bar", height: 320, toolbar: { show: false } },
			series: [{ name: "Documents", data: charts.document_volume.values }],
			xaxis: { categories: charts.document_volume.labels },
			colors: ["#112033"],
			plotOptions: { bar: { borderRadius: 6, columnWidth: "52%" } },
			dataLabels: { enabled: true },
		});
	}

	draw_chart(id, options) {
		const target = this.$root.find(`#${id}`)[0];
		if (!target) {
			return;
		}

		if (this.charts[id]) {
			this.charts[id].destroy();
		}

		if (!window.ApexCharts) {
			target.innerHTML = '<div class="empty-state">ApexCharts failed to load.</div>';
			return;
		}

		const hasData = (options.series || []).some((series) => {
			if (Array.isArray(series)) {
				return series.length;
			}
			if (Array.isArray(series?.data)) {
				return series.data.length;
			}
			return typeof series === "number";
		});

		if (!hasData && !(options.labels || []).length) {
			target.innerHTML = '<div class="empty-state">No chart data for this range.</div>';
			return;
		}

		target.innerHTML = "";
		this.charts[id] = new ApexCharts(target, options);
		this.charts[id].render();
	}

	format_value(value, label) {
		return ["Sales", "Collections", "Expenses"].includes(label)
			? format_currency(value)
			: format_number(value, null, 0);
	}

	short_currency(value) {
		if (Math.abs(value) >= 1000000) {
			return `${(value / 1000000).toFixed(1)}M`;
		}
		if (Math.abs(value) >= 1000) {
			return `${(value / 1000).toFixed(1)}K`;
		}
		return format_number(value, null, 0);
	}
}
