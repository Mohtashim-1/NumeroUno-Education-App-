frappe.pages["overtime-dashboard"].on_page_load = function (wrapper) {
	if (!wrapper.overtimeDashboard) {
		wrapper.overtimeDashboard = new OvertimeDashboard(wrapper);
	}
};

frappe.pages["overtime-dashboard"].refresh = function (wrapper) {
	wrapper.overtimeDashboard?.refresh();
};

class OvertimeDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Overtime Dashboard",
			single_column: true,
		});

		this.page.set_primary_action(__("New Overtime Request"), () => {
			frappe.new_doc("Overtime Request");
		});

		this.page.set_secondary_action(__("View Requests"), () => {
			frappe.set_route("List", "Overtime Request");
		});

		this.filters = {};
		this.inject_style();
		this.page.main.html(this.get_template());
		this.$root = $(this.page.main).find(".ot-page");
		this.$summary = this.$root.find('[data-region="summary"]');
		this.$status = this.$root.find('[data-region="status"]');
		this.$departments = this.$root.find('[data-region="departments"]');
		this.$employees = this.$root.find('[data-region="employees"]');
		this.$recent = this.$root.find('[data-region="recent"]');
		this.$range = this.$root.find('[data-region="range"]');

		this.make_filters();
		this.bind_events();
		this.refresh();
	}

	get_template() {
		return `
			<div class="ot-page">
				<div class="ot-hero">
					<div>
						<h2>Overtime Dashboard</h2>
						<p>Overtime request history from Overtime Request, including approved, rejected, pending, and employee-wise approval history.</p>
					</div>
					<div class="ot-range" data-region="range">Loading range...</div>
				</div>

				<div class="ot-panel ot-filters">
					<div class="ot-filter-grid" data-region="filters"></div>
				</div>

				<div class="ot-summary-grid" data-region="summary"></div>

				<div class="ot-layout">
					<div class="ot-panel">
						<h3>Status Overview</h3>
						<div class="ot-note">Current overtime approval queue by workflow stage.</div>
						<div data-region="status"></div>
					</div>
					<div class="ot-panel">
						<h3>Department Hours</h3>
						<div class="ot-note">Top departments by overtime hours in the selected range.</div>
						<div data-region="departments"></div>
					</div>
				</div>

				<div class="ot-panel">
					<h3>Employee Approval History</h3>
					<div class="ot-note">See past employee requests and how many were approved, rejected, or still pending.</div>
					<div data-region="employees"></div>
				</div>

				<div class="ot-panel">
					<h3>Recent Overtime Requests</h3>
					<div class="ot-note">Latest overtime submissions with request details, hours, and status.</div>
					<div data-region="recent"></div>
				</div>
			</div>
		`;
	}

	make_filters() {
		const $target = this.$root.find('[data-region="filters"]');
		const fields = [
			{ fieldtype: "Date", fieldname: "from_date", label: "From Date", default: frappe.datetime.month_start() },
			{ fieldtype: "Date", fieldname: "to_date", label: "To Date", default: frappe.datetime.get_today() },
			{ fieldtype: "Link", fieldname: "department", label: "Department", options: "Department" },
			{ fieldtype: "Link", fieldname: "employee", label: "Employee", options: "Employee" },
			{
				fieldtype: "Select",
				fieldname: "status",
				label: "Status",
				options: "\nDraft\nPending Direct Manager\nPending Next Manager\nPending HR\nApproved\nRejected",
			},
		];

		fields.forEach((df) => {
			const $field = $('<div class="ot-filter-cell"></div>').appendTo($target);
			const control = frappe.ui.form.make_control({
				df,
				parent: $field,
				render_input: true,
			});
			control.refresh();
			control.set_value(df.default || "");
			this.filters[df.fieldname] = control;
		});

		const $actions = $('<div class="ot-filter-actions"></div>').appendTo($target);
		this.applyButton = $('<button class="btn btn-primary">Apply</button>').appendTo($actions);
		this.resetButton = $('<button class="btn btn-default">Reset</button>').appendTo($actions);
	}

	bind_events() {
		this.applyButton.on("click", () => this.refresh());
		this.resetButton.on("click", () => this.reset_filters());
		Object.values(this.filters).forEach((control) => {
			control.$input && control.$input.on("change", () => this.refresh());
		});
	}

	get_filter_values() {
		return Object.fromEntries(Object.entries(this.filters).map(([key, control]) => [key, control.get_value()]));
	}

	reset_filters() {
		this.filters.from_date.set_value(frappe.datetime.month_start());
		this.filters.to_date.set_value(frappe.datetime.get_today());
		this.filters.department.set_value("");
		this.filters.employee.set_value("");
		this.filters.status.set_value("");
		this.refresh();
	}

	refresh() {
		frappe.call({
			method: "numerouno.numerouno.page.overtime_dashboard.overtime_dashboard.get_overtime_dashboard_data",
			args: { filters: this.get_filter_values() },
			freeze: false,
			callback: (r) => {
				if (!r.message) return;
				this.render(r.message);
			},
			error: () => {
				frappe.show_alert({ message: __("Unable to load overtime dashboard"), indicator: "red" });
			},
		});
	}

	render(data) {
		this.$range.text(`${frappe.datetime.str_to_user(data.filters.from_date)} to ${frappe.datetime.str_to_user(data.filters.to_date)}`);
		this.render_summary(data.summary || {});
		this.render_status(data.status_rows || []);
		this.render_departments(data.department_rows || []);
		this.render_employees(data.employee_rows || []);
		this.render_recent(data.recent_requests || []);
	}

	render_summary(summary) {
		const cards = [
			{ label: "Total Requests", value: format_number(summary.total_requests || 0, null, 0), cls: "" },
			{ label: "Total Hours", value: format_number(summary.total_hours || 0, null, 2), cls: "" },
			{ label: "Approved Hours", value: format_number(summary.approved_hours || 0, null, 2), cls: "approved" },
			{ label: "Rejected Hours", value: format_number(summary.rejected_hours || 0, null, 2), cls: "rejected" },
			{ label: "Pending Hours", value: format_number(summary.pending_hours || 0, null, 2), cls: "pending" },
			{ label: "Sunday Requests", value: format_number(summary.sunday_requests || 0, null, 0), cls: "" },
			{ label: "Sunday Hours", value: format_number(summary.sunday_hours || 0, null, 2), cls: "" },
			{ label: "Avg Hours / Request", value: format_number(summary.average_hours || 0, null, 2), cls: "" },
		];

		this.$summary.html(cards.map((card) => `
			<div class="ot-card ${card.cls}">
				<div class="ot-card-label">${frappe.utils.escape_html(card.label)}</div>
				<div class="ot-card-value">${card.value}</div>
			</div>
		`).join(""));
	}

	render_status(rows) {
		if (!rows.length) {
			this.$status.html('<div class="ot-empty">No status data found.</div>');
			return;
		}

		this.$status.html(`
			<div class="ot-list">
				${rows.map((row) => `
					<div class="ot-list-row">
						<div>
							<strong>${frappe.utils.escape_html(row.label)}</strong>
							<span>${frappe.utils.escape_html(row.note || "")}</span>
						</div>
						<div class="ot-badge">${format_number(row.count || 0, null, 0)}</div>
					</div>
				`).join("")}
			</div>
		`);
	}

	render_departments(rows) {
		if (!rows.length) {
			this.$departments.html('<div class="ot-empty">No department totals found.</div>');
			return;
		}

		this.$departments.html(`
			<table class="ot-table">
				<thead>
					<tr>
						<th>Department</th>
						<th>Requests</th>
						<th>Hours</th>
					</tr>
				</thead>
				<tbody>
					${rows.map((row) => `
						<tr>
							<td>${frappe.utils.escape_html(row.label || "")}</td>
							<td>${format_number(row.requests || 0, null, 0)}</td>
							<td>${format_number(row.hours || 0, null, 2)}</td>
						</tr>
					`).join("")}
				</tbody>
			</table>
		`);
	}

	render_employees(rows) {
		if (!rows.length) {
			this.$employees.html('<div class="ot-empty">No employee overtime history found.</div>');
			return;
		}

		this.$employees.html(`
			<div class="ot-table-wrap">
				<table class="ot-table">
					<thead>
						<tr>
							<th>Employee</th>
							<th>Department</th>
							<th>Total Req</th>
							<th>Total Hours</th>
							<th>Approved</th>
							<th>Approved Hours</th>
							<th>Rejected</th>
							<th>Rejected Hours</th>
							<th>Pending</th>
							<th>Pending Hours</th>
						</tr>
					</thead>
					<tbody>
						${rows.map((row) => `
							<tr>
								<td>${frappe.utils.escape_html(row.label || "")}</td>
								<td>${frappe.utils.escape_html(row.department || "")}</td>
								<td>${format_number(row.total_requests || 0, null, 0)}</td>
								<td>${format_number(row.total_hours || 0, null, 2)}</td>
								<td>${format_number(row.approved_requests || 0, null, 0)}</td>
								<td>${format_number(row.approved_hours || 0, null, 2)}</td>
								<td>${format_number(row.rejected_requests || 0, null, 0)}</td>
								<td>${format_number(row.rejected_hours || 0, null, 2)}</td>
								<td>${format_number(row.pending_requests || 0, null, 0)}</td>
								<td>${format_number(row.pending_hours || 0, null, 2)}</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
			</div>
		`);
	}

	render_recent(rows) {
		if (!rows.length) {
			this.$recent.html('<div class="ot-empty">No overtime requests found for this range.</div>');
			return;
		}

		this.$recent.html(`
			<div class="ot-table-wrap">
				<table class="ot-table">
					<thead>
						<tr>
							<th>Request</th>
							<th>Date</th>
							<th>Employee</th>
							<th>Department</th>
							<th>Time From</th>
							<th>Time To</th>
							<th>Hours</th>
							<th>Status</th>
							<th>Reason</th>
						</tr>
					</thead>
					<tbody>
						${rows.map((row) => `
							<tr>
								<td>${frappe.utils.escape_html(row.name || "")}</td>
								<td>${frappe.datetime.str_to_user(row.date)}</td>
								<td>${frappe.utils.escape_html(row.employee_name || row.employee || "")}</td>
								<td>${frappe.utils.escape_html(row.department || "")}</td>
								<td>${frappe.utils.escape_html(row.time_from || "")}</td>
								<td>${frappe.utils.escape_html(row.time_to || "")}</td>
								<td>${format_number(row.overtime_hours || 0, null, 2)}</td>
								<td><span class="ot-status ot-${frappe.scrub(row.effective_status || row.workflow_state || row.status || "Draft")}">${frappe.utils.escape_html(row.effective_status || row.workflow_state || row.status || "Draft")}</span></td>
								<td>${frappe.utils.escape_html(row.reason_for_work || "")}</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
			</div>
		`);
	}

	inject_style() {
		if ($("#overtime-dashboard-style").length) return;

		$(`<style id="overtime-dashboard-style">
			.ot-page {
				--ot-bg: linear-gradient(180deg, #fffdf8 0%, #f5f9ff 100%);
				--ot-panel: #ffffff;
				--ot-border: #e5eaf2;
				--ot-ink: #14213d;
				--ot-muted: #667085;
				--ot-blue: #2563eb;
				--ot-green: #16a34a;
				--ot-red: #dc2626;
				--ot-gold: #d97706;
				background: var(--ot-bg);
				padding: 24px;
				border-radius: 18px;
				color: var(--ot-ink);
			}
			.ot-hero {
				display: flex;
				justify-content: space-between;
				align-items: flex-start;
				gap: 16px;
				margin-bottom: 18px;
			}
			.ot-hero h2 {
				margin: 0 0 8px;
				font-size: 32px;
				font-weight: 800;
			}
			.ot-hero p,
			.ot-note,
			.ot-range,
			.ot-card-label {
				color: var(--ot-muted);
			}
			.ot-range {
				background: #fff;
				border: 1px solid var(--ot-border);
				border-radius: 999px;
				padding: 10px 14px;
				font-size: 12px;
				font-weight: 700;
				white-space: nowrap;
			}
			.ot-panel,
			.ot-card {
				background: var(--ot-panel);
				border: 1px solid var(--ot-border);
				border-radius: 18px;
				box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
			}
			.ot-panel {
				padding: 18px;
				margin-bottom: 18px;
			}
			.ot-panel h3 {
				margin: 0 0 8px;
				font-size: 22px;
			}
			.ot-filter-grid {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 14px;
				align-items: end;
			}
			.ot-filter-actions {
				display: flex;
				gap: 10px;
				align-items: center;
			}
			.ot-summary-grid {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 14px;
				margin-bottom: 18px;
			}
			.ot-card {
				padding: 18px;
			}
			.ot-card.pending {
				background: linear-gradient(180deg, #fffdf8 0%, #fff4dc 100%);
				border-color: #f4d192;
			}
			.ot-card.approved {
				background: linear-gradient(180deg, #fafffc 0%, #e8f8ee 100%);
				border-color: #b9e5c8;
			}
			.ot-card.rejected {
				background: linear-gradient(180deg, #fffafa 0%, #fdecec 100%);
				border-color: #f0c0c0;
			}
			.ot-card-value {
				margin-top: 8px;
				font-size: 24px;
				font-weight: 800;
			}
			.ot-layout {
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 16px;
			}
			.ot-list {
				display: grid;
				gap: 10px;
			}
			.ot-list-row {
				display: flex;
				justify-content: space-between;
				align-items: center;
				gap: 12px;
				padding: 12px 14px;
				background: #f8fbff;
				border-radius: 12px;
			}
			.ot-list-row strong {
				display: block;
				margin-bottom: 4px;
			}
			.ot-list-row span {
				font-size: 12px;
				color: var(--ot-muted);
			}
			.ot-badge,
			.ot-status {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				border-radius: 999px;
				padding: 4px 10px;
				font-size: 11px;
				font-weight: 700;
				white-space: nowrap;
			}
			.ot-status.ot-approved { background: #e8f8ee; color: #137a38; }
			.ot-status.ot-rejected { background: #fdecec; color: #b42318; }
			.ot-status.ot-pending-direct-manager,
			.ot-status.ot-pending-next-manager,
			.ot-status.ot-pending-hr,
			.ot-status.ot-draft { background: #fff4dc; color: #9a6700; }
			.ot-table-wrap {
				overflow: auto;
			}
			.ot-table {
				width: 100%;
				border-collapse: collapse;
			}
			.ot-table th,
			.ot-table td {
				padding: 12px 10px;
				border-bottom: 1px solid var(--ot-border);
				text-align: left;
				font-size: 13px;
				vertical-align: top;
			}
			.ot-table th {
				font-size: 11px;
				text-transform: uppercase;
				letter-spacing: 0.06em;
				color: var(--ot-muted);
				background: #f8fbff;
				position: sticky;
				top: 0;
			}
			.ot-empty {
				padding: 16px;
				border-radius: 12px;
				background: #f8fbff;
				color: var(--ot-muted);
				text-align: center;
				font-size: 13px;
			}
			@media (max-width: 991px) {
				.ot-layout {
					grid-template-columns: 1fr;
				}
			}
		</style>`).appendTo("head");
	}
}
