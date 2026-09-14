frappe.pages["invoice-print-tracker"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales Invoice Tracking"),
		single_column: true,
	});

	new SalesInvoiceTrackingPage(page);
};

class SalesInvoiceTrackingPage {
	constructor(page) {
		this.page = page;
		this.rows = [];
		this.print_format = "Sales Invoice NUTC";
		this.make_filters();
		this.make_layout();
		this.bind_actions();
		this.refresh();
	}

	make_filters() {
		this.view_filter = this.page.add_field({
			fieldname: "view",
			label: __("Show"),
			fieldtype: "Select",
			options: [
				{ value: "needs_print", label: __("Needs Print") },
				{ value: "done", label: __("Printed / Done") },
				{ value: "all", label: __("All Invoices") },
			],
			default: "needs_print",
			change: () => this.refresh(),
		});
		this.customer_filter = this.page.add_field({
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
			change: () => this.refresh(),
		});
		this.from_date_filter = this.page.add_field({
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			change: () => this.refresh(),
		});
		this.to_date_filter = this.page.add_field({
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			change: () => this.refresh(),
		});
		this.search_filter = this.page.add_field({
			fieldname: "search",
			label: __("Search"),
			fieldtype: "Data",
			change: () => this.refresh(),
		});
	}

	make_layout() {
		this.$root = $(`
			<div class="sit-page">
				
				<div class="sit-stats row text-muted small mb-3"></div>
				<div class="sit-table-wrap"></div>
			</div>
		`);
		this.page.main.append(this.$root);
		this.$stats = this.$root.find(".sit-stats");
		this.$table_wrap = this.$root.find(".sit-table-wrap");
	}

	bind_actions() {
		this.page.set_primary_action(__("Save"), () => this.save(), "save");
		this.page.add_inner_button(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Print Selected"), () => this.print_selected(), "print");
	}

	get_filters() {
		return {
			view: this.view_filter.get_value() || "needs_print",
			customer: this.customer_filter.get_value(),
			from_date: this.from_date_filter.get_value(),
			to_date: this.to_date_filter.get_value(),
			search: this.search_filter.get_value(),
		};
	}

	refresh() {
		frappe.call({
			method: "numerouno.numerouno.page.invoice_print_tracker.invoice_print_tracker.get_invoices",
			args: { filters: this.get_filters() },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				const msg = r.message || {};
				this.rows = (msg.rows || []).map((row) => ({ ...row, _selected: false }));
				this.print_format = msg.print_format || this.print_format;
				this.render_stats(msg);
				this.render_table();
			},
		});
	}

	render_stats(msg) {
		const view = this.get_filters().view;
		let hint = __("Showing {0} invoice(s)", [msg.count || 0]);
		if (view === "needs_print") {
			hint += ` — ${__("invoices waiting to be printed")}`;
		}
		this.$stats.html(`<div class="col-12">${hint}</div>`);
	}

	render_table() {
		if (!this.rows.length) {
			this.$table_wrap.html(
				`<div class="text-muted p-4 text-center">${__("No invoices match this filter.")}</div>`
			);
			return;
		}

		const header = `
			<table class="table table-bordered table-hover sit-table">
				<thead>
					<tr>
						<th><input type="checkbox" class="sit-select-all" title="${__("Select")}"></th>
						<th>${__("Invoice")}</th>
						<th>${__("Customer")}</th>
						<th>${__("Date")}</th>
						<th>${__("Grand Total")}</th>
						<th>${__("Print Status")}</th>
						<th>${__("Email Sent")}</th>
						<th>${__("Original Sent")}</th>
						<th>${__("Remarks")}</th>
						<th></th>
					</tr>
				</thead>
				<tbody></tbody>
			</table>`;
		this.$table_wrap.html(header);
		const $tbody = this.$table_wrap.find("tbody");

		this.rows.forEach((row, idx) => {
			const status = row.printed
				? `<span class="indicator-pill green">${__("Printed")}</span>`
				: `<span class="indicator-pill orange">${__("Not printed")}</span>`;
			const printed_meta = row.printed_on
				? `<div class="text-muted small">${frappe.datetime.str_to_user(row.printed_on)}</div>`
				: "";
			$tbody.append(`
				<tr data-idx="${idx}">
					<td><input type="checkbox" class="sit-row-select" data-idx="${idx}"></td>
					<td><a href="/app/sales-invoice/${encodeURIComponent(row.invoice_number)}">${frappe.utils.escape_html(
						row.invoice_number
					)}</a></td>
					<td>${frappe.utils.escape_html(row.customer_name || row.customer || "")}</td>
					<td>${frappe.datetime.str_to_user(row.invoice_date)}</td>
					<td>${frappe.format(row.grand_total, { fieldtype: "Currency", options: row.currency })}</td>
					<td>${status}${printed_meta}</td>
					<td class="text-center"><input type="checkbox" class="sit-email" data-idx="${idx}" ${
						row.email_sent ? "checked" : ""
					}></td>
					<td class="text-center"><input type="checkbox" class="sit-original" data-idx="${idx}" ${
						row.original_sent ? "checked" : ""
					}></td>
					<td><input type="text" class="form-control input-sm sit-remarks" data-idx="${idx}" value="${frappe.utils.escape_html(
						row.remarks || ""
					)}"></td>
					<td><button class="btn btn-default btn-xs sit-print-one" data-invoice="${frappe.utils.escape_html(
						row.invoice_number
					)}">${__("Print")}</button></td>
				</tr>
			`);
		});

		this.$table_wrap.find(".sit-select-all").on("change", (e) => {
			const checked = e.target.checked;
			this.$table_wrap.find(".sit-row-select").prop("checked", checked);
		});

		this.$table_wrap.find(".sit-print-one").on("click", (e) => {
			const invoice = $(e.currentTarget).data("invoice");
			this.print_invoices([invoice], true);
		});
	}

	collect_rows_for_save() {
		return this.rows.map((row, idx) => {
			const $tr = this.$table_wrap.find(`tr[data-idx="${idx}"]`);
			if (!$tr.length) return null;
			return {
				invoice_number: row.invoice_number,
				email_sent: $tr.find(".sit-email").is(":checked") ? 1 : 0,
				original_sent: $tr.find(".sit-original").is(":checked") ? 1 : 0,
				remarks: $tr.find(".sit-remarks").val(),
				printed: row.printed ? 1 : 0,
			};
		}).filter(Boolean);
	}

	get_selected_invoices() {
		const selected = [];
		this.$table_wrap.find(".sit-row-select:checked").each((_, el) => {
			const idx = $(el).data("idx");
			if (this.rows[idx]) selected.push(this.rows[idx].invoice_number);
		});
		return selected;
	}

	save() {
		const payload = this.collect_rows_for_save();
		frappe.call({
			method: "numerouno.numerouno.page.invoice_print_tracker.invoice_print_tracker.save_tracking_rows",
			args: { rows: payload },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				frappe.show_alert({
					message: __("Saved {0} row(s)", [(r.message || {}).updated || 0]),
					indicator: "green",
				});
				this.refresh();
			},
		});
	}

	print_selected() {
		const invoices = this.get_selected_invoices();
		if (!invoices.length) {
			frappe.msgprint(__("Select at least one invoice to print."));
			return;
		}
		this.print_invoices(invoices, true);
	}

	print_invoices(invoices, mark_printed) {
		invoices.forEach((name) => {
			const url = frappe.urllib.get_full_url(
				`/printview?doctype=${encodeURIComponent("Sales Invoice")}&name=${encodeURIComponent(
					name
				)}&format=${encodeURIComponent(this.print_format)}&trigger_print=1`
			);
			window.open(url, "_blank");
		});

		if (!mark_printed) return;

		frappe.call({
			method: "numerouno.numerouno.page.invoice_print_tracker.invoice_print_tracker.mark_printed",
			args: { invoice_numbers: invoices, open_print: 0 },
			callback: (r) => {
				if (r.exc) return;
				frappe.show_alert({
					message: __("Marked {0} invoice(s) as printed", [((r.message || {}).marked || []).length]),
					indicator: "green",
				});
				this.refresh();
			},
		});
	}
}
