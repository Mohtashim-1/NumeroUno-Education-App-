frappe.pages['asset-management-portal'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Asset Management Portal',
		single_column: true
	});

	var $body = $(`
		<style>
			.asset-management-portal {
				--ink: #132033;
				--muted: #617083;
				--surface: #ffffff;
				--surface-soft: #f5f7fa;
				--line: #dde4ed;
				--accent: #1f8a84;
				--accent-dark: #14635f;
				--amber: #d97706;
				--danger: #c2410c;
				font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
				color: var(--ink);
				background:
					radial-gradient(900px 420px at -10% -20%, rgba(31, 138, 132, 0.18), transparent 64%),
					radial-gradient(900px 380px at 110% 0%, rgba(217, 119, 6, 0.12), transparent 60%),
					linear-gradient(180deg, #f6f8fb 0%, #edf3f5 52%, #f9fafb 100%);
				border-radius: 18px;
				padding: 28px;
				margin-top: 12px;
			}

			.asset-hero {
				display: grid;
				grid-template-columns: minmax(260px, 0.9fr) minmax(360px, 1.5fr);
				gap: 20px;
				align-items: start;
				margin-bottom: 22px;
			}

			.asset-hero-copy h2 {
				margin: 0;
				font-size: 28px;
				font-weight: 750;
				letter-spacing: 0;
			}

			.asset-hero-copy p {
				margin: 8px 0 0;
				color: var(--muted);
				font-size: 14px;
				line-height: 1.55;
				max-width: 560px;
			}

			.asset-metrics {
				display: grid;
				grid-template-columns: repeat(4, minmax(130px, 1fr));
				gap: 12px;
			}

			.asset-metric-card {
				background: var(--surface);
				border: 1px solid rgba(221, 228, 237, 0.9);
				border-radius: 14px;
				padding: 14px 16px;
				box-shadow: 0 12px 26px rgba(19, 32, 51, 0.08);
				min-height: 96px;
			}

			.asset-metric-card h5 {
				margin: 0 0 8px;
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: var(--muted);
			}

			.asset-metric-card .value {
				font-size: 26px;
				font-weight: 760;
				color: var(--ink);
				line-height: 1.1;
			}

			.asset-metric-card small {
				display: block;
				margin-top: 6px;
				color: var(--muted);
				font-size: 12px;
			}

			.asset-filters {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 12px;
				margin: 18px 0;
				align-items: end;
			}

			.asset-filters .frappe-control {
				margin-bottom: 0;
			}

			.asset-filters .control-label {
				font-size: 12px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: var(--muted);
				margin-bottom: 6px;
			}

			.asset-filters .control-input,
			.asset-filters .form-control,
			.asset-filters .input-with-feedback {
				border-radius: 12px;
				border: 1px solid var(--line);
				background: #ffffff;
				box-shadow: none;
			}

			.asset-filter-actions {
				display: flex;
				align-items: end;
				gap: 8px;
				min-height: 60px;
			}

			.asset-btn {
				border: 0;
				border-radius: 999px;
				padding: 8px 15px;
				font-size: 13px;
				font-weight: 700;
				line-height: 1.2;
				cursor: pointer;
				text-decoration: none;
				display: inline-flex;
				align-items: center;
				justify-content: center;
				gap: 6px;
				white-space: nowrap;
			}

			.asset-btn-primary {
				background: var(--accent);
				color: #ffffff;
				box-shadow: 0 10px 22px rgba(31, 138, 132, 0.22);
			}

			.asset-btn-ghost {
				background: #ffffff;
				color: var(--ink);
				border: 1px solid var(--line);
			}

			.asset-btn-small {
				padding: 6px 10px;
				font-size: 12px;
			}

			.asset-row-actions {
				display: flex;
				gap: 6px;
				flex-wrap: wrap;
			}

			.asset-focus-bar {
				display: none;
				align-items: center;
				justify-content: space-between;
				gap: 12px;
				background: #e7f4f3;
				border: 1px solid #b9dfdc;
				border-radius: 14px;
				padding: 10px 12px;
				margin: 0 0 14px;
				color: var(--accent-dark);
				font-size: 13px;
				font-weight: 700;
			}

			.asset-focus-bar.active {
				display: flex;
			}

			.asset-tabs {
				display: flex;
				gap: 10px;
				flex-wrap: wrap;
				margin: 8px 0 18px;
			}

			.asset-tab {
				border: 1px solid var(--line);
				background: #ffffff;
				color: var(--ink);
				border-radius: 999px;
				padding: 8px 16px;
				font-size: 13px;
				font-weight: 700;
				cursor: pointer;
			}

			.asset-tab.active {
				background: var(--accent);
				border-color: var(--accent);
				color: #ffffff;
			}

			.asset-section[hidden] {
				display: none;
			}

			.asset-panel {
				background: var(--surface);
				border: 1px solid rgba(221, 228, 237, 0.9);
				border-radius: 18px;
				box-shadow: 0 12px 30px rgba(19, 32, 51, 0.08);
				padding: 18px;
			}

			.asset-panel-header {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 12px;
				margin-bottom: 12px;
			}

			.asset-panel-title {
				display: flex;
				gap: 12px;
				align-items: center;
			}

			.asset-panel-title span {
				width: 38px;
				height: 38px;
				border-radius: 12px;
				background: #e7f4f3;
				color: var(--accent-dark);
				display: inline-flex;
				align-items: center;
				justify-content: center;
				font-size: 12px;
				font-weight: 800;
			}

			.asset-panel-title h3 {
				margin: 0;
				font-size: 17px;
				font-weight: 750;
			}

			.asset-panel-title p {
				margin: 3px 0 0;
				color: var(--muted);
				font-size: 13px;
			}

			.asset-management-portal .table {
				margin-bottom: 0;
				background: transparent;
			}

			.asset-management-portal th {
				font-size: 11px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: var(--muted);
				border-top: 0;
				white-space: nowrap;
			}

			.asset-management-portal td {
				vertical-align: middle;
				font-size: 13px;
				color: var(--ink);
			}

			.asset-cell-title {
				display: block;
				margin-top: 3px;
				color: var(--muted);
				font-size: 12px;
				line-height: 1.25;
			}

			.asset-pill {
				display: inline-flex;
				align-items: center;
				border-radius: 999px;
				padding: 4px 9px;
				font-size: 12px;
				font-weight: 700;
				background: var(--surface-soft);
				color: var(--ink);
				white-space: nowrap;
			}

			.asset-pill.high,
			.asset-pill.overdue {
				background: #fff1e8;
				color: var(--danger);
			}

			.asset-pill.medium,
			.asset-pill.due {
				background: #fff7df;
				color: var(--amber);
			}

			.asset-pill.low,
			.asset-pill.ok {
				background: #e7f4f3;
				color: var(--accent-dark);
			}

			.asset-muted {
				color: var(--muted);
			}

			.asset-empty-state {
				text-align: center;
				color: var(--muted);
				padding: 22px 0;
			}

			@media (max-width: 980px) {
				.asset-hero {
					grid-template-columns: 1fr;
				}

				.asset-metrics {
					grid-template-columns: repeat(2, minmax(140px, 1fr));
				}
			}

			@media (max-width: 640px) {
				.asset-management-portal {
					padding: 18px;
				}

				.asset-metrics {
					grid-template-columns: 1fr;
				}
			}
		</style>

		<div class="asset-management-portal">
			<div class="asset-hero">
				<div class="asset-hero-copy">
					<h2>Asset Management Portal</h2>
					<p>Operational view for assets, maintenance planning, certification renewals, and critical equipment status.</p>
					<div style="margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;">
						<a class="asset-btn asset-btn-primary" href="/app/asset/new">New Asset</a>
						<button type="button" class="asset-btn asset-btn-ghost" id="jump-maintenance">Maintenance</button>
						<button type="button" class="asset-btn asset-btn-ghost" id="jump-compliance">Compliance</button>
					</div>
				</div>
				<div class="asset-metrics">
					<div class="asset-metric-card">
						<h5>Total Assets</h5>
						<div class="value" id="metric-total-assets">0</div>
						<small>Filtered asset count</small>
					</div>
					<div class="asset-metric-card">
						<h5>In Maintenance</h5>
						<div class="value" id="metric-in-maintenance">0</div>
						<small>Assets currently under service</small>
					</div>
					<div class="asset-metric-card">
						<h5>Overdue Tasks</h5>
						<div class="value" id="metric-overdue">0</div>
						<small>Maintenance logs overdue</small>
					</div>
					<div class="asset-metric-card">
						<h5>Certificates Due</h5>
						<div class="value" id="metric-certificates">0</div>
						<small>Expiring in 30 days</small>
					</div>
				</div>
			</div>

			<div class="asset-filters">
				<div id="filter-asset-category"></div>
				<div id="filter-location"></div>
				<div id="filter-department"></div>
				<div id="filter-status"></div>
				<div id="filter-criticality"></div>
				<div class="asset-filter-actions">
					<button type="button" class="asset-btn asset-btn-primary" id="asset-apply-filters">Apply</button>
					<button type="button" class="asset-btn asset-btn-ghost" id="asset-reset-filters">Reset</button>
				</div>
			</div>

			<div class="asset-tabs">
				<button type="button" class="asset-tab active" data-target="asset-register-section">Asset Register</button>
				<button type="button" class="asset-tab" data-target="maintenance-section">Maintenance Plan</button>
				<button type="button" class="asset-tab" data-target="compliance-section">Compliance</button>
			</div>

			<div class="asset-focus-bar" id="asset-focus-bar">
				<span id="asset-focus-label"></span>
				<button type="button" class="asset-btn asset-btn-small asset-btn-ghost" id="asset-clear-focus">Show All Assets</button>
			</div>

			<div class="asset-section" id="asset-register-section">
				<div class="asset-panel">
					<div class="asset-panel-header">
						<div class="asset-panel-title">
							<span>AR</span>
							<div>
								<h3>Asset Register</h3>
								<p>Core asset information, status, warranty, and reliability indicators.</p>
							</div>
						</div>
						<a class="asset-btn asset-btn-ghost" href="/app/asset">Open List</a>
					</div>
					<div class="table-responsive">
						<table class="table">
							<thead>
								<tr>
									<th>Asset</th>
									<th>Tag</th>
									<th>Category</th>
									<th>Location</th>
									<th>Status</th>
									<th>Model</th>
									<th>Warranty</th>
									<th>MTBF / MTTR</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody id="asset-register-body">
								<tr><td colspan="9" class="asset-empty-state">Loading...</td></tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<div class="asset-section" id="maintenance-section" hidden>
				<div class="asset-panel">
					<div class="asset-panel-header">
						<div class="asset-panel-title">
							<span>MP</span>
							<div>
								<h3>Maintenance Plan</h3>
								<p>Strategy, SLA expiry, criticality, and open task load.</p>
							</div>
						</div>
						<a class="asset-btn asset-btn-ghost" href="/app/asset-maintenance">Open List</a>
					</div>
					<div class="table-responsive">
						<table class="table">
							<thead>
								<tr>
									<th>Maintenance</th>
									<th>Asset</th>
									<th>Strategy</th>
									<th>Criticality</th>
									<th>Team</th>
									<th>SLA Expiry</th>
									<th>Open / Overdue</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody id="maintenance-plan-body">
								<tr><td colspan="8" class="asset-empty-state">Loading...</td></tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<div class="asset-section" id="compliance-section" hidden>
				<div class="asset-panel">
					<div class="asset-panel-header">
						<div class="asset-panel-title">
							<span>CP</span>
							<div>
								<h3>Compliance & Certification</h3>
								<p>Certificate expiry, recertification urgency, and assigned owners.</p>
							</div>
						</div>
						<a class="asset-btn asset-btn-ghost" href="/app/asset-maintenance-log">Logs</a>
					</div>
					<div class="table-responsive">
						<table class="table">
							<thead>
								<tr>
									<th>Task</th>
									<th>Asset</th>
									<th>Type</th>
									<th>Frequency</th>
									<th>Owner</th>
									<th>Next Due</th>
									<th>Certificate Expiry</th>
									<th>Urgency</th>
								</tr>
							</thead>
							<tbody id="compliance-body">
								<tr><td colspan="8" class="asset-empty-state">Loading...</td></tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	`).appendTo(page.body);

	var filterState = {
		asset_category: "",
		location: "",
		department: "",
		status: "",
		criticality: "",
		asset_name: ""
	};
	var filterControls = {};

	init_filters();
	init_tabs();
	load_portal_data();

	function init_filters() {
		filterControls.asset_category = make_filter_control({
			label: "Asset Category",
			fieldname: "asset_category",
			fieldtype: "Link",
			options: "Asset Category",
			parent: $("#filter-asset-category")
		});
		filterControls.location = make_filter_control({
			label: "Location",
			fieldname: "location",
			fieldtype: "Link",
			options: "Location",
			parent: $("#filter-location")
		});
		filterControls.department = make_filter_control({
			label: "Department",
			fieldname: "department",
			fieldtype: "Link",
			options: "Department",
			parent: $("#filter-department")
		});
		filterControls.status = make_filter_control({
			label: "Asset Status",
			fieldname: "status",
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nPartially Depreciated\nFully Depreciated\nSold\nScrapped\nIn Maintenance\nOut of Order\nWork In Progress",
			parent: $("#filter-status")
		});
		filterControls.criticality = make_filter_control({
			label: "Criticality",
			fieldname: "criticality",
			fieldtype: "Select",
			options: "\nHigh\nMedium\nLow",
			parent: $("#filter-criticality")
		});

		$("#asset-apply-filters").on("click", apply_filters);
		$("#asset-reset-filters").on("click", function () {
			Object.values(filterControls).forEach(function (control) {
				control.set_value("");
			});
			filterState.asset_name = "";
			apply_filters();
		});
		$("#asset-clear-focus").on("click", function () {
			filterState.asset_name = "";
			load_portal_data();
		});
		$("#jump-maintenance").on("click", function () {
			show_section("maintenance-section");
		});
		$("#jump-compliance").on("click", function () {
			show_section("compliance-section");
		});
	}

	function make_filter_control(config) {
		var control = frappe.ui.form.make_control({
			parent: config.parent,
			df: {
				fieldtype: config.fieldtype || "Link",
				fieldname: config.fieldname,
				label: config.label,
				options: config.options,
				change: function () {
					filterState[config.fieldname] = control.get_value() || "";
				}
			},
			render_input: true
		});
		return control;
	}

	function apply_filters() {
		Object.keys(filterControls).forEach(function (key) {
			filterState[key] = filterControls[key].get_value() || "";
		});
		filterState.asset_name = "";
		load_portal_data();
	}

	function init_tabs() {
		$(".asset-tab").on("click", function () {
			show_section($(this).data("target"));
		});
	}

	function show_section(target) {
		$(".asset-tab").removeClass("active");
		$(`.asset-tab[data-target="${target}"]`).addClass("active");
		$(".asset-section").attr("hidden", true);
		$(`#${target}`).removeAttr("hidden");
	}

	function load_portal_data() {
		set_loading();
		frappe.call({
			method: "numerouno.numerouno.page.asset_management_portal.asset_management_portal.get_asset_management_portal_data",
			args: filterState,
			callback: function (r) {
				var message = r.message || {};
				render_metrics(message.metrics || {});
				render_focus();
				render_assets(message.assets || []);
				render_maintenance(message.maintenance || []);
				render_compliance(message.compliance || []);
			},
			error: function () {
				render_assets([]);
				render_maintenance([]);
				render_compliance([]);
				frappe.msgprint("Unable to load asset management data.");
			}
		});
	}

	function set_loading() {
		$("#asset-register-body").html(`<tr><td colspan="9" class="asset-empty-state">Loading...</td></tr>`);
		$("#maintenance-plan-body").html(`<tr><td colspan="8" class="asset-empty-state">Loading...</td></tr>`);
		$("#compliance-body").html(`<tr><td colspan="8" class="asset-empty-state">Loading...</td></tr>`);
	}

	function render_focus() {
		if (filterState.asset_name) {
			$("#asset-focus-label").text(`Showing maintenance and compliance for ${filterState.asset_name}`);
			$("#asset-focus-bar").addClass("active");
		} else {
			$("#asset-focus-bar").removeClass("active");
			$("#asset-focus-label").text("");
		}
	}

	function render_metrics(metrics) {
		$("#metric-total-assets").text(metrics.total_assets || 0);
		$("#metric-in-maintenance").text(metrics.in_maintenance || 0);
		$("#metric-overdue").text(metrics.overdue_tasks || 0);
		$("#metric-certificates").text(metrics.certificates_due || 0);
	}

	function render_assets(rows) {
		if (!rows.length) {
			$("#asset-register-body").html(`<tr><td colspan="9" class="asset-empty-state">No assets found.</td></tr>`);
			return;
		}
		$("#asset-register-body").html(rows.map(function (row) {
			var model = [row.custom_manufacturer, row.custom_model].filter(Boolean).join(" / ") || "-";
			var reliability = `${format_number(row.custom_mtbf_hours)} / ${format_number(row.custom_mttr_hours)}`;
			return `
				<tr>
					<td><a href="/app/asset/${encodeURIComponent(row.name)}">${escape_html(row.asset_name || row.name)}</a></td>
					<td>${escape_html(row.custom_asset_tag_number || "-")}</td>
					<td>${escape_html(row.asset_category || "-")}</td>
					<td>${escape_html(row.location || "-")}</td>
					<td>${status_pill(row.status)}</td>
					<td>${escape_html(model)}</td>
					<td>${format_date(row.custom_warranty_expiry_date)}</td>
					<td>${escape_html(reliability)}</td>
					<td>
						<div class="asset-row-actions">
							<button type="button" class="asset-btn asset-btn-small asset-btn-primary asset-maintenance-action" data-asset="${escape_attr(row.name)}" data-asset-title="${escape_attr(row.asset_name || row.name)}">Maintenance</button>
							<button type="button" class="asset-btn asset-btn-small asset-btn-ghost asset-compliance-action" data-asset="${escape_attr(row.name)}" data-asset-title="${escape_attr(row.asset_name || row.name)}">Compliance</button>
						</div>
					</td>
				</tr>
			`;
		}).join(""));
		bind_asset_row_actions();
	}

	function bind_asset_row_actions() {
		$(".asset-maintenance-action").off("click").on("click", function () {
			open_maintenance_dialog($(this).data("asset"), $(this).data("asset-title"));
		});
		$(".asset-compliance-action").off("click").on("click", function () {
			open_compliance_dialog($(this).data("asset"), $(this).data("asset-title"));
		});
	}

	function open_maintenance_dialog(asset_name, asset_title) {
		var dialog = new frappe.ui.Dialog({
			title: `Plan Maintenance - ${asset_title || asset_name}`,
			fields: [
				{
					fieldtype: "Link",
					fieldname: "asset_name",
					label: "Asset",
					options: "Asset",
					default: asset_name,
					read_only: 1
				},
				{
					fieldtype: "Link",
					fieldname: "maintenance_team",
					label: "Maintenance Team",
					options: "Asset Maintenance Team",
					reqd: 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Link",
					fieldname: "assign_to",
					label: "Assign To",
					options: "User",
					reqd: 1
				},
				{
					fieldtype: "Section Break",
					label: "Plan"
				},
				{
					fieldtype: "Data",
					fieldname: "maintenance_task",
					label: "Maintenance Task",
					reqd: 1
				},
				{
					fieldtype: "Select",
					fieldname: "strategy",
					label: "Maintenance Strategy",
					options: "\nPreventive\nPredictive\nCorrective\nCondition-based",
					default: "Preventive"
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Select",
					fieldname: "maintenance_type",
					label: "Maintenance Type",
					options: "Preventive Maintenance\nCalibration",
					default: "Preventive Maintenance"
				},
				{
					fieldtype: "Select",
					fieldname: "criticality",
					label: "Criticality",
					options: "\nHigh\nMedium\nLow"
				},
				{
					fieldtype: "Section Break",
					label: "Schedule"
				},
				{
					fieldtype: "Select",
					fieldname: "periodicity",
					label: "Frequency",
					options: "Daily\nWeekly\nMonthly\nQuarterly\nHalf-yearly\nYearly\n2 Yearly\n3 Yearly",
					default: "Monthly",
					reqd: 1
				},
				{
					fieldtype: "Date",
					fieldname: "start_date",
					label: "Start Date",
					default: frappe.datetime.nowdate(),
					reqd: 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Int",
					fieldname: "reminder_days_before",
					label: "Email Reminder Days Before",
					default: 7
				},
				{
					fieldtype: "Date",
					fieldname: "sla_expiry_date",
					label: "SLA Expiry Date"
				},
				{
					fieldtype: "Section Break",
					label: "SLA"
				},
				{
					fieldtype: "Duration",
					fieldname: "sla_response_time",
					label: "SLA Response Time"
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Duration",
					fieldname: "sla_resolution_time",
					label: "SLA Resolution Time"
				},
				{
					fieldtype: "Section Break",
					label: "Checklist"
				},
				{
					fieldtype: "Text Editor",
					fieldname: "checklist",
					label: "Maintenance Checklist"
				}
			],
			primary_action_label: "Create Maintenance",
			primary_action: function (values) {
				frappe.call({
					method: "numerouno.numerouno.page.asset_management_portal.asset_management_portal.create_asset_maintenance_from_portal",
					args: values,
					freeze: true,
					freeze_message: "Creating maintenance record...",
					callback: function (r) {
						dialog.hide();
						after_record_created(r.message, "maintenance-section", "Maintenance record created");
					}
				});
			}
		});
		dialog.show();
	}

	function open_compliance_dialog(asset_name, asset_title) {
		var dialog = new frappe.ui.Dialog({
			title: `Add Compliance - ${asset_title || asset_name}`,
			fields: [
				{
					fieldtype: "Link",
					fieldname: "asset_name",
					label: "Asset",
					options: "Asset",
					default: asset_name,
					read_only: 1
				},
				{
					fieldtype: "Link",
					fieldname: "maintenance_team",
					label: "Maintenance Team",
					options: "Asset Maintenance Team",
					reqd: 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Link",
					fieldname: "assign_to",
					label: "Responsible Person",
					options: "User",
					reqd: 1
				},
				{
					fieldtype: "Section Break",
					label: "Certificate"
				},
				{
					fieldtype: "Data",
					fieldname: "compliance_task",
					label: "Compliance / Certificate Task",
					reqd: 1
				},
				{
					fieldtype: "Date",
					fieldname: "certificate_expiry_date",
					label: "Certificate Expiry Date",
					reqd: 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Select",
					fieldname: "periodicity",
					label: "Recertification Frequency",
					options: "Daily\nWeekly\nMonthly\nQuarterly\nHalf-yearly\nYearly\n2 Yearly\n3 Yearly",
					default: "Yearly",
					reqd: 1
				},
				{
					fieldtype: "Date",
					fieldname: "start_date",
					label: "Start Date",
					default: frappe.datetime.nowdate(),
					reqd: 1
				},
				{
					fieldtype: "Section Break",
					label: "Reminder"
				},
				{
					fieldtype: "Int",
					fieldname: "recertification_reminder_days",
					label: "Reminder Days Before Expiry",
					default: 30
				},
				{
					fieldtype: "Select",
					fieldname: "criticality",
					label: "Criticality",
					options: "\nHigh\nMedium\nLow"
				},
				{
					fieldtype: "Section Break",
					label: "Checklist"
				},
				{
					fieldtype: "Text Editor",
					fieldname: "checklist",
					label: "Compliance Checklist / Notes"
				}
			],
			primary_action_label: "Create Compliance",
			primary_action: function (values) {
				frappe.call({
					method: "numerouno.numerouno.page.asset_management_portal.asset_management_portal.create_asset_compliance_from_portal",
					args: values,
					freeze: true,
					freeze_message: "Creating compliance record...",
					callback: function (r) {
						dialog.hide();
						after_record_created(r.message, "compliance-section", "Compliance record created");
					}
				});
			}
		});
		dialog.show();
	}

	function after_record_created(message, target, alert_message) {
		message = message || {};
		filterState.asset_name = message.asset_name || filterState.asset_name;
		load_portal_data();
		show_section(target);
		frappe.show_alert({
			message: alert_message,
			indicator: "green"
		});
	}

	function render_maintenance(rows) {
		if (!rows.length) {
			$("#maintenance-plan-body").html(`<tr><td colspan="8" class="asset-empty-state">No maintenance plans found.</td></tr>`);
			return;
		}
		$("#maintenance-plan-body").html(rows.map(function (row) {
			const assetTitle = row.asset_title && row.asset_title !== row.asset_name
				? `<span class="asset-cell-title">${escape_html(row.asset_title)}</span>`
				: "";
			return `
				<tr>
					<td><a href="/app/asset-maintenance/${encodeURIComponent(row.name)}">${escape_html(row.name)}</a></td>
					<td>
						<a href="/app/asset/${encodeURIComponent(row.asset_name || "")}">${escape_html(row.asset_name || "-")}</a>
						${assetTitle}
					</td>
					<td>${escape_html(row.custom_maintenance_strategy || "-")}</td>
					<td>${criticality_pill(row.custom_criticality_rating)}</td>
					<td>${escape_html(row.maintenance_team || "-")}</td>
					<td>${format_date(row.custom_sla_expiry_date)}</td>
					<td>${escape_html(row.open_tasks || 0)} / ${overdue_pill(row.overdue_tasks || 0)}</td>
					<td><a class="asset-btn asset-btn-ghost" href="/app/asset-maintenance/${encodeURIComponent(row.name)}">Open</a></td>
				</tr>
			`;
		}).join(""));
	}

	function render_compliance(rows) {
		if (!rows.length) {
			$("#compliance-body").html(`<tr><td colspan="8" class="asset-empty-state">No certificate records found.</td></tr>`);
			return;
		}
		$("#compliance-body").html(rows.map(function (row) {
			return `
				<tr>
					<td>${escape_html(row.maintenance_task || "-")}</td>
					<td>${escape_html(row.asset_name || "-")}</td>
					<td>${escape_html(row.maintenance_type || "-")}</td>
					<td>${escape_html(row.periodicity || "-")}</td>
					<td>${escape_html(row.assign_to_name || "-")}</td>
					<td>${format_date(row.next_due_date)}</td>
					<td>${format_date(row.custom_certificate_expiry_date)}</td>
					<td>${expiry_pill(row.days_to_expiry)}</td>
				</tr>
			`;
		}).join(""));
	}

	function status_pill(status) {
		var lowered = (status || "").toLowerCase();
		var cls = lowered.includes("maintenance") || lowered.includes("order") ? "due" : "ok";
		return `<span class="asset-pill ${cls}">${escape_html(status || "-")}</span>`;
	}

	function criticality_pill(value) {
		var cls = (value || "").toLowerCase();
		return `<span class="asset-pill ${cls || "ok"}">${escape_html(value || "-")}</span>`;
	}

	function overdue_pill(value) {
		var cls = value ? "overdue" : "ok";
		return `<span class="asset-pill ${cls}">${escape_html(value)}</span>`;
	}

	function expiry_pill(days) {
		if (days === undefined || days === null) {
			return `<span class="asset-pill">-</span>`;
		}
		var cls = days <= 0 ? "overdue" : (days <= 7 ? "due" : "ok");
		var label = days <= 0 ? "Expires today" : `${days} days`;
		return `<span class="asset-pill ${cls}">${escape_html(label)}</span>`;
	}

	function format_date(value) {
		return value ? frappe.datetime.str_to_user(value) : "-";
	}

	function format_number(value) {
		return value ? flt(value, 2) : "0";
	}

	function escape_html(value) {
		return frappe.utils.escape_html(String(value === undefined || value === null ? "" : value));
	}

	function escape_attr(value) {
		return escape_html(value).replace(/"/g, "&quot;");
	}
};
