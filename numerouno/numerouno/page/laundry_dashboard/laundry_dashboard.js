frappe.pages["laundry-dashboard"].on_page_load = function (wrapper) {
	new LaundryDashboard(wrapper);
};

class LaundryDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Laundry Dashboard",
			single_column: true,
		});

		this.page.set_primary_action(__("New Laundry Entry"), () => {
			frappe.new_doc("Laundry");
		});

		this.page.set_secondary_action(__("View Laundry List"), () => {
			frappe.set_route("List", "Laundry");
		});

		this.render();
		this.bind_events();
		this.load_report(frappe.datetime.get_today());
	}

	render() {
		this.wrapper.find(".layout-main-section").html(`
			<div class="laundry-dashboard">
				<div class="laundry-hero">
					<h1>Daily Laundry Report</h1>
					<p>Transaction & Missing Overview</p>
				</div>
				<div class="laundry-filter-card">
					<label for="laundry-report-date">Select Date</label>
					<div class="laundry-filter-row">
						<input type="date" id="laundry-report-date" class="form-control" value="${frappe.datetime.get_today()}">
						<button class="btn btn-primary" id="laundry-report-search">
							${frappe.utils.icon("search-sm", "sm")}
							<span>Search</span>
						</button>
					</div>
				</div>
				<div class="laundry-grid">
					<div class="laundry-panel laundry-panel-out">
						<div class="laundry-panel-title">OUT Details</div>
						<div id="laundry-out-table"></div>
					</div>
					<div class="laundry-panel laundry-panel-in">
						<div class="laundry-panel-title">IN Details</div>
						<div id="laundry-in-table"></div>
					</div>
				</div>
				<div class="laundry-panel laundry-panel-missing">
					<div class="laundry-panel-title">Missing Items (By Date)</div>
					<div id="laundry-missing-table"></div>
				</div>
			</div>
		`);

		this.inject_styles();
	}

	bind_events() {
		this.wrapper.on("click", "#laundry-report-search", () => {
			this.load_report(this.wrapper.find("#laundry-report-date").val());
		});

		this.wrapper.on("keydown", "#laundry-report-date", (event) => {
			if (event.key === "Enter") {
				this.load_report(this.wrapper.find("#laundry-report-date").val());
			}
		});
	}

	load_report(report_date) {
		frappe.call({
			method: "numerouno.numerouno.page.laundry_dashboard.laundry_dashboard.get_daily_report",
			args: { report_date },
			freeze: true,
			callback: ({ message }) => {
				const data = message || {};
				this.render_table("#laundry-out-table", ["Laundry ID", "Employee", "Item", "Qty", "Time"], data.out_rows || [], "No OUT records", (row) => [
					row.laundry_id,
					row.employee,
					row.item,
					row.qty,
					row.time || "-",
				]);
				this.render_table("#laundry-in-table", ["Laundry ID", "Employee", "Item", "Qty", "Time"], data.in_rows || [], "No IN records", (row) => [
					row.laundry_id,
					row.employee,
					row.item,
					row.qty,
					row.time || "-",
				]);
				this.render_table("#laundry-missing-table", ["Laundry ID", "Item", "Missing Qty"], data.missing_rows || [], "No Missing Items", (row) => [
					row.laundry_id,
					row.item,
					row.missing_qty,
				]);
			},
		});
	}

	render_table(selector, headers, rows, empty_text, map_row) {
		const table = `
			<table class="laundry-table">
				<thead>
					<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${rows.length ? rows.map((row) => `<tr>${map_row(row).map((value) => `<td>${frappe.utils.escape_html(String(value))}</td>`).join("")}</tr>`).join("") : `<tr><td colspan="${headers.length}" class="laundry-empty">${frappe.utils.escape_html(empty_text)}</td></tr>`}
				</tbody>
			</table>
		`;
		this.wrapper.find(selector).html(table);
	}

	inject_styles() {
		if (document.getElementById("laundry-dashboard-styles")) return;

		const style = document.createElement("style");
		style.id = "laundry-dashboard-styles";
		style.textContent = `
			.laundry-dashboard {
				padding: 18px 8px 32px;
				background: linear-gradient(180deg, #f8fafc 0%, #eef4f8 100%);
				min-height: calc(100vh - 120px);
			}
			.laundry-hero {
				text-align: center;
				margin-bottom: 24px;
			}
			.laundry-hero h1 {
				margin: 0;
				font-size: 42px;
				font-weight: 800;
				color: #0f172a;
			}
			.laundry-hero p {
				margin: 6px 0 0;
				font-size: 20px;
				color: #475467;
			}
			.laundry-filter-card,
			.laundry-panel {
				background: #fff;
				border-radius: 24px;
				padding: 20px 18px;
				box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
				margin-bottom: 20px;
			}
			.laundry-filter-card label {
				display: block;
				font-size: 22px;
				font-weight: 700;
				margin-bottom: 12px;
				color: #0f172a;
			}
			.laundry-filter-row {
				display: flex;
				gap: 16px;
				align-items: center;
			}
			.laundry-filter-row input {
				max-width: 340px;
				height: 46px;
				font-size: 18px;
			}
			.laundry-filter-row .btn {
				height: 46px;
				padding: 0 22px;
				display: inline-flex;
				align-items: center;
				gap: 8px;
				font-size: 18px;
			}
			.laundry-grid {
				display: grid;
				grid-template-columns: repeat(2, minmax(0, 1fr));
				gap: 20px;
			}
			.laundry-panel-title {
				font-size: 20px;
				font-weight: 800;
				margin-bottom: 14px;
			}
			.laundry-panel-out .laundry-panel-title {
				color: #dc2626;
			}
			.laundry-panel-in .laundry-panel-title {
				color: #059669;
			}
			.laundry-panel-missing .laundry-panel-title {
				color: #d97706;
			}
			.laundry-table {
				width: 100%;
				border-collapse: collapse;
				font-size: 15px;
			}
			.laundry-table th,
			.laundry-table td {
				border: 1px solid #d0d5dd;
				padding: 12px 10px;
				text-align: left;
			}
			.laundry-panel-out .laundry-table th {
				background: #fee2e2;
			}
			.laundry-panel-in .laundry-table th {
				background: #d1fae5;
			}
			.laundry-panel-missing .laundry-table th {
				background: #fef3c7;
			}
			.laundry-empty {
				text-align: center;
				color: #667085;
				font-size: 18px;
			}
			@media (max-width: 991px) {
				.laundry-grid {
					grid-template-columns: 1fr;
				}
				.laundry-filter-row {
					flex-direction: column;
					align-items: stretch;
				}
				.laundry-filter-row input {
					max-width: none;
				}
			}
		`;
		document.head.appendChild(style);
	}
}
