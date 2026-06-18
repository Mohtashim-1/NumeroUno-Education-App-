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

			.asset-pagination {
				display: flex;
				align-items: center;
				justify-content: flex-end;
				gap: 10px;
				flex-wrap: wrap;
				margin-top: 12px;
				color: var(--muted);
				font-size: 12px;
				font-weight: 700;
			}

			.asset-pagination select {
				border: 1px solid var(--line);
				border-radius: 10px;
				background: #ffffff;
				padding: 6px 28px 6px 10px;
				color: var(--ink);
				font-weight: 700;
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
					<div class="asset-pagination" data-section="assets">
						<span id="assets-page-info">Showing 0 of 0</span>
						<label>Rows <select class="asset-page-size" data-section="assets">
							<option value="20" selected>20</option>
							<option value="50">50</option>
							<option value="100">100</option>
							<option value="500">500</option>
						</select></label>
						<button type="button" class="asset-btn asset-btn-ghost asset-load-more" data-section="assets">Load More</button>
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
					<div class="asset-pagination" data-section="maintenance">
						<span id="maintenance-page-info">Showing 0 of 0</span>
						<label>Rows <select class="asset-page-size" data-section="maintenance">
							<option value="20" selected>20</option>
							<option value="50">50</option>
							<option value="100">100</option>
							<option value="500">500</option>
						</select></label>
						<button type="button" class="asset-btn asset-btn-ghost asset-load-more" data-section="maintenance">Load More</button>
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
								<p>Upload or renew compliance certificates on the asset. Previous files are archived automatically.</p>
							</div>
						</div>
						<div style="display:flex; gap:8px; flex-wrap:wrap;">
							<a class="asset-btn asset-btn-ghost" href="/app/query-report/Asset%20Document%20History">Document History</a>
							<a class="asset-btn asset-btn-ghost" href="/app/asset-maintenance-log">Logs</a>
						</div>
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
									<th>Certificate</th>
									<th>Urgency</th>
								</tr>
							</thead>
							<tbody id="compliance-body">
								<tr><td colspan="9" class="asset-empty-state">Loading...</td></tr>
							</tbody>
						</table>
					</div>
					<div class="asset-pagination" data-section="compliance">
						<span id="compliance-page-info">Showing 0 of 0</span>
						<label>Rows <select class="asset-page-size" data-section="compliance">
							<option value="20" selected>20</option>
							<option value="50">50</option>
							<option value="100">100</option>
							<option value="500">500</option>
						</select></label>
						<button type="button" class="asset-btn asset-btn-ghost asset-load-more" data-section="compliance">Load More</button>
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
	var pageState = {
		assets: { limit: 20, offset: 0, loaded: 0, total: 0 },
		maintenance: { limit: 20, offset: 0, loaded: 0, total: 0 },
		compliance: { limit: 20, offset: 0, loaded: 0, total: 0 }
	};

	init_filters();
	init_tabs();
	init_pagination();
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
			reset_pagination();
			apply_filters();
		});
		$("#asset-clear-focus").on("click", function () {
			filterState.asset_name = "";
			reset_pagination();
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
		reset_pagination();
		load_portal_data();
	}

	function init_pagination() {
		$(".asset-page-size").on("change", function () {
			var section = $(this).data("section");
			pageState[section].limit = cint($(this).val()) || 20;
			reset_pagination();
			load_portal_data();
		});

		$(".asset-load-more").on("click", function () {
			var section = $(this).data("section");
			pageState[section].offset = pageState[section].loaded;
			load_portal_data({ append_section: section });
		});
	}

	function reset_pagination() {
		Object.keys(pageState).forEach(function (section) {
			pageState[section].offset = 0;
			pageState[section].loaded = 0;
		});
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

	function load_portal_data(options) {
		options = options || {};
		var appendSection = options.append_section || "";
		if (!appendSection) {
			set_loading();
		}
		frappe.call({
			method: "numerouno.numerouno.page.asset_management_portal.asset_management_portal.get_asset_management_portal_data",
			args: get_portal_args(),
			callback: function (r) {
				var message = r.message || {};
				render_metrics(message.metrics || {});
				render_focus();
				update_pagination_state(message.pagination || {}, message, appendSection);
				if (!appendSection || appendSection === "assets") {
					render_assets(message.assets || [], appendSection === "assets");
				}
				if (!appendSection || appendSection === "maintenance") {
					render_maintenance(message.maintenance || [], appendSection === "maintenance");
				}
				if (!appendSection || appendSection === "compliance") {
					render_compliance(message.compliance || [], appendSection === "compliance");
				}
				render_pagination_controls();
			},
			error: function () {
				render_assets([]);
				render_maintenance([]);
				render_compliance([]);
				frappe.msgprint("Unable to load asset management data.");
			}
		});
	}

	function get_portal_args() {
		return Object.assign({}, filterState, {
			asset_limit: pageState.assets.limit,
			asset_offset: pageState.assets.offset,
			maintenance_limit: pageState.maintenance.limit,
			maintenance_offset: pageState.maintenance.offset,
			compliance_limit: pageState.compliance.limit,
			compliance_offset: pageState.compliance.offset
		});
	}

	function update_pagination_state(pagination, message, appendSection) {
		if (appendSection) {
			var totalKey = appendSection === "assets" ? "asset_total" : `${appendSection}_total`;
			update_section_page_state(appendSection, pagination[totalKey], message[appendSection] || []);
			return;
		}

		update_section_page_state("assets", pagination.asset_total, message.assets || []);
		update_section_page_state("maintenance", pagination.maintenance_total, message.maintenance || []);
		update_section_page_state("compliance", pagination.compliance_total, message.compliance || []);
	}

	function update_section_page_state(section, total, rows) {
		var state = pageState[section];
		state.total = cint(total) || 0;
		if (state.offset === 0) {
			state.loaded = rows.length;
		} else {
			state.loaded = Math.min(state.offset + rows.length, state.total);
		}
	}

	function render_pagination_controls() {
		render_section_pagination("assets");
		render_section_pagination("maintenance");
		render_section_pagination("compliance");
	}

	function render_section_pagination(section) {
		var state = pageState[section];
		$(`#${section}-page-info`).text(`Showing ${state.loaded} of ${state.total}`);
		$(`.asset-load-more[data-section="${section}"]`).prop("disabled", state.loaded >= state.total);
	}

	function set_loading() {
		$("#asset-register-body").html(`<tr><td colspan="9" class="asset-empty-state">Loading...</td></tr>`);
		$("#maintenance-plan-body").html(`<tr><td colspan="8" class="asset-empty-state">Loading...</td></tr>`);
		$("#compliance-body").html(`<tr><td colspan="9" class="asset-empty-state">Loading...</td></tr>`);
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

	function render_assets(rows, append) {
		if (!rows.length) {
			if (!append) {
				$("#asset-register-body").html(`<tr><td colspan="9" class="asset-empty-state">No assets found.</td></tr>`);
			}
			return;
		}
		var html = rows.map(function (row) {
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
							<button type="button" class="asset-btn asset-btn-small asset-btn-ghost asset-documents-action" data-asset="${escape_attr(row.name)}" data-asset-title="${escape_attr(row.asset_name || row.name)}">Documents</button>
						</div>
					</td>
				</tr>
			`;
		}).join("");
		if (append) {
			$("#asset-register-body").append(html);
		} else {
			$("#asset-register-body").html(html);
		}
		bind_asset_row_actions();
	}

	function bind_asset_row_actions() {
		$(".asset-maintenance-action").off("click").on("click", function () {
			open_maintenance_dialog($(this).data("asset"), $(this).data("asset-title"));
		});
		$(".asset-compliance-action").off("click").on("click", function () {
			open_compliance_dialog($(this).data("asset"), $(this).data("asset-title"));
		});
		$(".asset-documents-action").off("click").on("click", function () {
			open_documents_dialog($(this).data("asset"), $(this).data("asset-title"));
		});
	}

	function open_documents_dialog(asset_name, asset_title) {
		frappe.call({
			method: "numerouno.numerouno.asset_document_archive.get_asset_documents",
			args: { asset_name: asset_name },
			freeze: true,
			freeze_message: "Loading documents...",
			callback: function (r) {
				var data = r.message || {};
				var dialog = new frappe.ui.Dialog({
					title: `Documents - ${asset_title || asset_name}`,
					size: "large",
					fields: [
						{
							fieldtype: "HTML",
							fieldname: "documents_html"
						}
					],
					primary_action_label: "Add / Renew Document",
					primary_action: function () {
						open_renew_document_dialog(asset_name, asset_title, data.document_types || [], function () {
							dialog.hide();
							open_documents_dialog(asset_name, asset_title);
						});
					},
					secondary_action_label: "Add Compliance Certificate",
					secondary_action: function () {
						open_compliance_certificate_dialog(asset_name, asset_title, {
							expiry_date: (data.compliance_certificate || {}).expiry_date,
							has_certificate: !!(data.compliance_certificate || {}).document,
							on_success: function () {
								dialog.hide();
								open_documents_dialog(asset_name, asset_title);
							}
						});
					}
				});
				dialog.fields_dict.documents_html.$wrapper.html(render_documents_html(data));
				dialog.fields_dict.documents_html.$wrapper.find(".asset-inline-compliance-cert-action").on("click", function () {
					open_compliance_certificate_dialog($(this).data("asset"), $(this).data("asset-title"), {
						expiry_date: $(this).data("expiry"),
						has_certificate: $(this).data("has-cert") == 1,
						on_success: function () {
							dialog.hide();
							open_documents_dialog(asset_name, asset_title);
						}
					});
				});
				dialog.show();
			}
		});
	}

	function render_documents_html(data) {
		var compliance = data.compliance_certificate || {};
		var complianceSection = `
			<div style="margin-bottom:18px; padding:14px; border:1px solid var(--line, #dde4ed); border-radius:12px; background:#f8fbfa;">
				<div style="display:flex; justify-content:space-between; gap:12px; align-items:center; flex-wrap:wrap;">
					<div>
						<h4 style="margin:0 0 6px;">Compliance Certificate</h4>
						<p class="asset-muted" style="margin:0;">Saved on Asset field: <strong>custom_compliance_certificate</strong></p>
					</div>
					<button type="button" class="asset-btn asset-btn-primary asset-inline-compliance-cert-action"
						data-asset="${escape_attr(data.asset_name)}"
						data-asset-title="${escape_attr(data.asset_title || data.asset_name)}"
						data-expiry="${escape_attr(compliance.expiry_date || "")}"
						data-has-cert="${compliance.document ? "1" : "0"}">
						${compliance.document ? "Renew Certificate" : "Add Certificate"}
					</button>
				</div>
				<div style="margin-top:12px; display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:10px;">
					<div><span class="asset-muted">Current File</span><br>${compliance.document ? `<a href="${escape_attr(compliance.document)}" target="_blank" rel="noopener">View Certificate</a>` : "-"}</div>
					<div><span class="asset-muted">Expiry</span><br>${format_date(compliance.expiry_date)}</div>
				</div>
			</div>
		`;

		var currentRows = (data.current_documents || []).map(function (row) {
			return `
				<tr>
					<td>${escape_html(row.document_type)}</td>
					<td><a href="${escape_attr(row.document)}" target="_blank" rel="noopener">View Current</a></td>
					<td>${format_date(row.effective_from)}</td>
					<td>${format_date(row.expiry_date)}</td>
					<td><span class="asset-pill ok">Current</span></td>
				</tr>
			`;
		}).join("");

		var archivedRows = (data.archived_documents || []).map(function (row) {
			return `
				<tr>
					<td>${escape_html(row.document_type)}</td>
					<td><a href="${escape_attr(row.document)}" target="_blank" rel="noopener">View Archived</a></td>
					<td>${format_date(row.effective_from)}</td>
					<td>${format_date(row.expiry_date)}</td>
					<td>${format_date(row.archived_on)}</td>
					<td>${escape_html(row.archived_by || "-")}</td>
					<td>${escape_html(row.notes || "-")}</td>
				</tr>
			`;
		}).join("");

		return `
			${complianceSection}
			<div style="margin-bottom:18px;">
				<h4 style="margin:0 0 10px;">Current Documents</h4>
				<div class="table-responsive">
					<table class="table">
						<thead>
							<tr>
								<th>Type</th>
								<th>File</th>
								<th>Effective From</th>
								<th>Expiry</th>
								<th>Status</th>
							</tr>
						</thead>
						<tbody>${currentRows || `<tr><td colspan="5" class="asset-empty-state">No current documents uploaded.</td></tr>`}</tbody>
					</table>
				</div>
			</div>
			<div>
				<h4 style="margin:0 0 10px;">Archived / History</h4>
				<p class="asset-muted" style="margin:0 0 10px;">When a document is renewed, the previous file is kept here automatically.</p>
				<div class="table-responsive">
					<table class="table">
						<thead>
							<tr>
								<th>Type</th>
								<th>File</th>
								<th>Effective From</th>
								<th>Expiry</th>
								<th>Archived On</th>
								<th>Archived By</th>
								<th>Notes</th>
							</tr>
						</thead>
						<tbody>${archivedRows || `<tr><td colspan="7" class="asset-empty-state">No archived documents yet.</td></tr>`}</tbody>
					</table>
				</div>
			</div>
		`;
	}

	function open_renew_document_dialog(asset_name, asset_title, document_types, on_success, defaults) {
		defaults = defaults || {};
		var isRenewal = !!defaults.has_certificate;
		var renewDialog = new frappe.ui.Dialog({
			title: `${isRenewal ? "Renew" : "Add"} Document - ${asset_title || asset_name}`,
			fields: [
				{
					fieldtype: "Select",
					fieldname: "document_type",
					label: "Document Type",
					options: ["", ...(document_types || [])],
					default: defaults.document_type || "",
					read_only: defaults.document_type ? 1 : 0,
					reqd: 1
				},
				{
					fieldtype: "Attach",
					fieldname: "file_url",
					label: defaults.document_type ? `${defaults.document_type} File` : "Document File",
					reqd: 1
				},
				{
					fieldtype: "Column Break"
				},
				{
					fieldtype: "Date",
					fieldname: "effective_from",
					label: "Effective From",
					default: defaults.effective_from || ""
				},
				{
					fieldtype: "Date",
					fieldname: "expiry_date",
					label: "Expiry Date",
					default: defaults.expiry_date || "",
					reqd: defaults.document_type === "Compliance Certificate" ? 1 : 0
				},
				{
					fieldtype: "Section Break"
				},
				{
					fieldtype: "Small Text",
					fieldname: "notes",
					label: "Notes",
					default: defaults.notes || ""
				}
			],
			primary_action_label: isRenewal ? "Save Renewal" : "Save Document",
			primary_action: function (values) {
				frappe.call({
					method: "numerouno.numerouno.asset_document_archive.renew_asset_document",
					args: {
						asset_name: asset_name,
						document_type: values.document_type,
						file_url: values.file_url,
						expiry_date: values.expiry_date,
						effective_from: values.effective_from,
						notes: values.notes
					},
					freeze: true,
					freeze_message: "Saving document...",
					callback: function () {
						renewDialog.hide();
						frappe.show_alert({
							message: isRenewal ? "Document renewed. Previous file archived." : "Document saved successfully.",
							indicator: "green"
						});
						if (on_success) {
							on_success();
						}
					}
				});
			}
		});
		renewDialog.show();
	}

	function open_compliance_certificate_dialog(asset_name, asset_title, options) {
		options = options || {};
		open_renew_document_dialog(
			asset_name,
			asset_title,
			["Compliance Certificate"],
			function () {
				reset_pagination();
				load_portal_data();
				if (options.on_success) {
					options.on_success();
				}
			},
			{
				document_type: "Compliance Certificate",
				expiry_date: options.expiry_date || "",
				has_certificate: !!options.has_certificate
			}
		);
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
		reset_pagination();
		load_portal_data();
		show_section(target);
		frappe.show_alert({
			message: alert_message,
			indicator: "green"
		});
	}

	function render_maintenance(rows, append) {
		if (!rows.length) {
			if (!append) {
				$("#maintenance-plan-body").html(`<tr><td colspan="8" class="asset-empty-state">No maintenance plans found.</td></tr>`);
			}
			return;
		}
		var html = rows.map(function (row) {
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
		}).join("");
		if (append) {
			$("#maintenance-plan-body").append(html);
		} else {
			$("#maintenance-plan-body").html(html);
		}
	}

	function render_compliance(rows, append) {
		if (!rows.length) {
			if (!append) {
				$("#compliance-body").html(`<tr><td colspan="9" class="asset-empty-state">No certificate records found.</td></tr>`);
			}
			return;
		}
		var html = rows.map(function (row) {
			const assetLabel = row.asset_title && row.asset_title !== row.asset_name
				? `${escape_html(row.asset_name || "-")}<span class="asset-cell-title">${escape_html(row.asset_title)}</span>`
				: escape_html(row.asset_name || "-");
			const assetLink = row.asset_name
				? `<a href="/app/asset/${encodeURIComponent(row.asset_name)}">${assetLabel}</a>`
				: "-";
			const certificateLink = row.certificate_url
				? `<a class="asset-btn asset-btn-small asset-btn-ghost" href="${escape_attr(row.certificate_url)}" target="_blank" rel="noopener">View</a>`
				: "";
			const certActionLabel = row.certificate_url ? "Renew" : "Add";
			const certAction = row.asset_name
				? `<button type="button" class="asset-btn asset-btn-small asset-btn-primary asset-cert-upload-action"
					data-asset="${escape_attr(row.asset_name)}"
					data-asset-title="${escape_attr(row.asset_title || row.asset_name)}"
					data-expiry="${escape_attr(row.custom_certificate_expiry_date || "")}"
					data-has-cert="${row.certificate_url ? "1" : "0"}">${certActionLabel}</button>`
				: "-";
			return `
				<tr>
					<td>${escape_html(row.maintenance_task || "-")}</td>
					<td>${assetLink}</td>
					<td>${escape_html(row.maintenance_type || "-")}</td>
					<td>${escape_html(row.periodicity || "-")}</td>
					<td>${escape_html(row.assign_to_name || "-")}</td>
					<td>${format_date(row.next_due_date)}</td>
					<td>${format_date(row.custom_certificate_expiry_date)}</td>
					<td><div class="asset-row-actions">${certificateLink}${certAction}</div></td>
					<td>${expiry_pill(row.days_to_expiry)}</td>
				</tr>
			`;
		}).join("");
		if (append) {
			$("#compliance-body").append(html);
		} else {
			$("#compliance-body").html(html);
		}
		bind_compliance_row_actions();
	}

	function bind_compliance_row_actions() {
		$(".asset-cert-upload-action").off("click").on("click", function () {
			open_compliance_certificate_dialog($(this).data("asset"), $(this).data("asset-title"), {
				expiry_date: $(this).data("expiry"),
				has_certificate: $(this).data("has-cert") == 1
			});
		});
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
