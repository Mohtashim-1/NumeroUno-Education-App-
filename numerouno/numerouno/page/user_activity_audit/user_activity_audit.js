frappe.pages["user-activity-audit"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("User Activity Audit"),
		single_column: true,
	});

	new UserActivityAudit(page);
};

class UserActivityAudit {
	constructor(page) {
		this.page = page;
		this.data = null;
		this.make_filters();
		this.make_layout();
		this.bind_actions();
		this.refresh();
	}

	make_filters() {
		this.user = this.page.add_field({
			fieldname: "user",
			label: __("User"),
			fieldtype: "Link",
			options: "User",
		});
		this.from_date = this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
		});
		this.to_date = this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		});
		this.export_from = this.page.add_field({
			fieldname: "export_from",
			label: __("Export From"),
			fieldtype: "Data",
			description: __("e.g. Quotation, Customer, Sales Order"),
		});
		this.access_type = this.page.add_field({
			fieldname: "access_type",
			label: __("Route Access Type"),
			fieldtype: "Select",
			options: ["", "List", "Form", "Workspaces", "Report", "print"],
		});
		this.route_contains = this.page.add_field({
			fieldname: "route_contains",
			label: __("Route Contains"),
			fieldtype: "Data",
		});
		this.method = this.page.add_field({
			fieldname: "method",
			label: __("Access Log Method"),
			fieldtype: "Select",
			options: ["", "Print", "Export", "Download"],
		});
	}

	make_layout() {
		this.$root = $(`
			<div class="user-activity-audit">
				<div class="uaa-note alert alert-warning">
					<strong>${__("Data retention")}:</strong>
					${__(
						"Route History keeps navigation logs for 90 days. Access Log is the best source for print/export/PDF audit going back further."
					)}
				</div>
				<div class="uaa-summary row"></div>
				<div class="uaa-section card mb-4">
					<div class="card-header d-flex justify-content-between align-items-center">
						<h5 class="mb-0">${__("Navigation Activity (Route History)")}</h5>
						<span class="uaa-route-count badge badge-secondary"></span>
					</div>
					<div class="card-body p-0">
						<div class="uaa-route-table"></div>
					</div>
				</div>
				<div class="uaa-section card mb-4">
					<div class="card-header d-flex justify-content-between align-items-center">
						<h5 class="mb-0">${__("Print / Export Activity (Access Log)")}</h5>
						<span class="uaa-access-count badge badge-secondary"></span>
					</div>
					<div class="card-body p-0">
						<div class="uaa-access-table"></div>
					</div>
				</div>
			</div>
		`);
		this.page.main.append(this.$root);
	}

	bind_actions() {
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Export PDF"), () => this.export_file("pdf"), "pdf");
		this.page.add_inner_button(__("Export Word"), () => this.export_file("word"), "file");
		this.page.add_inner_button(__("Export Excel"), () => this.export_excel(), "excel");
	}

	get_filters() {
		return {
			user: this.user.get_value(),
			from_date: this.from_date.get_value(),
			to_date: this.to_date.get_value(),
			export_from: this.export_from.get_value(),
			access_type: this.access_type.get_value(),
			route_contains: this.route_contains.get_value(),
			method: this.method.get_value(),
			include_route_history: 1,
			include_access_log: 1,
		};
	}

	refresh() {
		frappe.dom.freeze(__("Loading activity data..."));
		frappe
			.call({
				method: "numerouno.numerouno.page.user_activity_audit.user_activity_audit.get_activity_data",
				args: { filters: this.get_filters() },
			})
			.then((r) => {
				this.data = r.message || {};
				this.render();
			})
			.always(() => frappe.dom.unfreeze());
	}

	render() {
		const summary = this.data.summary || {};
		this.render_summary(summary);
		this.render_route_table(this.data.route_history || []);
		this.render_access_table(this.data.access_log || []);
	}

	render_summary(summary) {
		const cards = [
			[__("Navigation Visits"), summary.route_visits || 0],
			[__("Access Log Entries"), summary.access_log_entries || 0],
			[__("Print / Export Actions"), summary.print_export_count || 0],
			[__("Quotation PDF Prints"), summary.quotation_print_count || 0],
			[__("Unique Routes"), summary.unique_routes || 0],
			[__("Unique Documents"), summary.unique_documents || 0],
		];

		const html = cards
			.map(
				([label, value]) => `
				<div class="col-md-4 col-lg-2 mb-3">
					<div class="uaa-kpi">
						<div class="uaa-kpi-value">${value}</div>
						<div class="uaa-kpi-label">${label}</div>
					</div>
				</div>`
			)
			.join("");

		const meta = `
			<div class="col-12 mb-3">
				<small class="text-muted">
					${__("Route History DB")}: ${summary.route_history_db_oldest || "-"}
					→ ${summary.route_history_db_newest || "-"}
					(${summary.route_history_db_total || 0} ${__("rows total")})
					| ${__("Generated")}: ${summary.generated_on || ""}
				</small>
			</div>`;

		this.$root.find(".uaa-summary").html(meta + html);
	}

	render_route_table(rows) {
		this.$root.find(".uaa-route-count").text(`${rows.length} ${__("rows")}`);

		if (!rows.length) {
			this.$root
				.find(".uaa-route-table")
				.html(`<div class="p-4 text-muted text-center">${__("No route history for selected filters.")}</div>`);
			return;
		}

		const table = this.build_datatable(
			[
				{ id: "accessed_on", name: __("Date/Time"), width: 170 },
				{ id: "user", name: __("User"), width: 180 },
				{ id: "full_name", name: __("Full Name"), width: 150 },
				{ id: "access_type", name: __("Access Type"), width: 100 },
				{ id: "accessed_item", name: __("Item"), width: 140 },
				{ id: "document", name: __("Document"), width: 160 },
				{ id: "route", name: __("Route"), width: 260 },
			],
			rows
		);
		this.$root.find(".uaa-route-table").html("").append(table);
	}

	render_access_table(rows) {
		this.$root.find(".uaa-access-count").text(`${rows.length} ${__("rows")}`);

		if (!rows.length) {
			this.$root
				.find(".uaa-access-table")
				.html(`<div class="p-4 text-muted text-center">${__("No access log entries for selected filters.")}</div>`);
			return;
		}

		const table = this.build_datatable(
			[
				{ id: "accessed_on", name: __("Date/Time"), width: 170 },
				{ id: "user", name: __("User"), width: 180 },
				{ id: "full_name", name: __("Full Name"), width: 150 },
				{ id: "export_from", name: __("Export From"), width: 120 },
				{ id: "reference_document", name: __("Document"), width: 170 },
				{ id: "file_type", name: __("File Type"), width: 90 },
				{ id: "method", name: __("Method"), width: 90 },
				{ id: "page", name: __("Page / Format"), width: 220, format: (row) => row.page || row.report_name || "" },
			],
			rows
		);
		this.$root.find(".uaa-access-table").html("").append(table);
	}

	build_datatable(columns, rows) {
		const $wrap = $('<div class="uaa-table-wrap"></div>');
		const $table = $('<table class="table table-bordered table-sm uaa-table mb-0"></table>');
		const $thead = $("<thead><tr></tr></thead>");
		columns.forEach((col) => {
			$thead.find("tr").append(`<th>${col.name}</th>`);
		});
		const $tbody = $("<tbody></tbody>");
		rows.forEach((row) => {
			const $tr = $("<tr></tr>");
			columns.forEach((col) => {
				const value = col.format ? col.format(row) : row[col.id];
				$tr.append(`<td>${frappe.utils.escape_html(String(value || ""))}</td>`);
			});
			$tbody.append($tr);
		});
		$table.append($thead).append($tbody);
		$wrap.append($table);
		return $wrap;
	}

	export_file(type) {
		const filters = this.get_filters();
		const method =
			type === "pdf"
				? "numerouno.numerouno.page.user_activity_audit.user_activity_audit.export_pdf"
				: "numerouno.numerouno.page.user_activity_audit.user_activity_audit.export_word";

		open_url_post(
			"/api/method/" + method,
			{ filters: JSON.stringify(filters) },
			true
		);
	}

	export_excel() {
		if (!this.data) {
			frappe.msgprint(__("Load data first"));
			return;
		}

		const rows = [];
		(this.data.route_history || []).forEach((r) => {
			rows.push({
				section: __("Route History"),
				date_time: r.accessed_on,
				user: r.user,
				full_name: r.full_name,
				access_type: r.access_type,
				item: r.accessed_item,
				document: r.document,
				route: r.route,
				export_from: "",
				file_type: "",
				method: "",
				page: "",
			});
		});
		(this.data.access_log || []).forEach((r) => {
			rows.push({
				section: __("Access Log"),
				date_time: r.accessed_on,
				user: r.user,
				full_name: r.full_name,
				access_type: "",
				item: "",
				document: r.reference_document,
				route: "",
				export_from: r.export_from,
				file_type: r.file_type,
				method: r.method,
				page: r.page || r.report_name,
			});
		});

		frappe.tools.downloadify(rows, null, __("User Activity Audit"));
	}
}
