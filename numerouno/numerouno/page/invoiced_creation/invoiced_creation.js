frappe.pages["invoiced-creation"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Invoiced Creation"),
		single_column: true,
	});

	new InvoicedCreationPage(page);
};

class InvoicedCreationPage {
	constructor(page) {
		this.page = page;
		this.customers = [];
		this.active_customer_index = 0;
		this.active_group_index = 0;
		this.selected_rows = new Set();
		this.make_filters();
		this.make_layout();
		this.bind_events();
		this.refresh();
	}

	make_filters() {
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
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
	}

	make_layout() {
		this.$root = $(`
			<div class="invoice-creation-page">
				<div class="invoice-actionbar">
					<div>
						<div class="action-title">${__("Invoice Workbench")}</div>
						<div class="action-subtitle selected-summary">${__("No pending students selected")}</div>
					</div>
					<div class="action-buttons">
						<label class="show-all-wrap">
							<input type="checkbox" class="show-all-customers">
							<span>${__("Show All Customers")}</span>
						</label>
						<button class="btn btn-default btn-sm select-visible-pending" disabled>${__("Select All Visible Pending")}</button>
						<button class="btn btn-default btn-sm select-customer-pending" disabled>${__("Select Customer Pending")}</button>
						<button class="btn btn-default btn-sm clear-selection" disabled>${__("Clear")}</button>
						<button class="btn btn-primary btn-sm create-invoice" disabled>${__("Create Invoice")}</button>
					</div>
				</div>
				<div class="invoice-toolbar">
					<div class="invoice-stat stat-customers" data-stat="customers"><span>0</span><div>${__("Customers")}</div></div>
					<div class="invoice-stat stat-pending" data-stat="pending"><span>0</span><div>${__("Pending")}</div></div>
					<div class="invoice-stat stat-process" data-stat="process"><span>0</span><div>${__("In Process")}</div></div>
					<div class="invoice-stat stat-invoiced" data-stat="invoiced"><span>0</span><div>${__("Invoiced")}</div></div>
				</div>
				<div class="invoice-workspace">
					<div class="invoice-pane customer-pane">
						<div class="pane-head">
							<div>
								<div class="pane-title">${__("Customers")}</div>
								<div class="pane-subtitle">${__("pending invoice queue")}</div>
							</div>
						</div>
						<div class="customer-list"></div>
					</div>
					<div class="invoice-pane group-pane">
						<div class="pane-head">
							<div>
								<div class="pane-title">${__("Student Groups")}</div>
								<div class="pane-subtitle group-summary">${__("choose a customer")}</div>
							</div>
							<label class="select-wrap">
								<input type="checkbox" class="select-all-groups">
								<span>${__("All Groups")}</span>
							</label>
						</div>
						<div class="group-list"></div>
					</div>
					<div class="invoice-pane student-pane">
						<div class="pane-head">
							<div>
								<div class="pane-title">${__("Students")}</div>
								<div class="pane-subtitle student-summary">${__("choose a group")}</div>
							</div>
							<label class="select-wrap student-select-wrap">
								<input type="checkbox" class="select-all-students">
								<span>${__("All Students")}</span>
							</label>
						</div>
						<div class="student-list"></div>
					</div>
				</div>
			</div>
		`).appendTo(this.page.body);

		this.$root.prepend(`
			<style>
				.invoice-creation-page {
					--invoice-line: #d9e2ec;
					--invoice-soft: #f6f8fb;
					--invoice-active: #eef6ff;
					--invoice-active-border: #228be6;
					--invoice-green: #168653;
					--invoice-green-bg: #e9f8f0;
					--invoice-orange: #b76e00;
					--invoice-orange-bg: #fff4df;
					--invoice-blue: #1f6feb;
					--invoice-blue-bg: #eaf2ff;
					--invoice-text: #263445;
					--invoice-muted: #667085;
				}
				.invoice-actionbar {
					display: flex;
					justify-content: space-between;
					align-items: center;
					gap: 16px;
					padding: 14px 16px;
					margin-bottom: 12px;
					border: 1px solid var(--invoice-line);
					border-radius: 8px;
					background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
				}
				.action-title { font-size: 16px; font-weight: 700; color: var(--invoice-text); }
				.action-subtitle { margin-top: 2px; font-size: 13px; color: var(--invoice-muted); }
				.action-buttons { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
				.show-all-wrap { display: flex; align-items: center; gap: 7px; margin: 0 8px 0 0; color: var(--invoice-text); font-weight: 500; white-space: nowrap; }
				.invoice-toolbar { display: grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap: 10px; margin-bottom: 12px; }
				.invoice-stat {
					border: 1px solid var(--invoice-line);
					border-radius: 8px;
					padding: 12px 14px;
					background: #fff;
					box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
				}
				.invoice-stat span { display: block; font-size: 24px; line-height: 1; font-weight: 750; color: var(--invoice-text); }
				.invoice-stat div { margin-top: 7px; font-size: 12px; color: var(--invoice-muted); }
				.stat-pending { border-top: 3px solid var(--invoice-green); }
				.stat-process { border-top: 3px solid var(--invoice-orange); }
				.stat-invoiced { border-top: 3px solid var(--invoice-blue); }
				.stat-customers { border-top: 3px solid #6b7280; }
				.invoice-workspace { display: grid; grid-template-columns: minmax(280px, .9fr) minmax(360px, 1.05fr) minmax(460px, 1.4fr); gap: 12px; min-height: 62vh; }
				.invoice-pane {
					border: 1px solid var(--invoice-line);
					border-radius: 8px;
					background: #fff;
					overflow: hidden;
					box-shadow: 0 1px 2px rgba(16, 24, 40, .04);
				}
				.pane-head {
					min-height: 58px;
					display: flex;
					align-items: center;
					justify-content: space-between;
					gap: 12px;
					padding: 10px 12px;
					border-bottom: 1px solid var(--invoice-line);
					background: var(--invoice-soft);
				}
				.pane-title { font-weight: 700; color: var(--invoice-text); }
				.pane-subtitle { margin-top: 1px; color: var(--invoice-muted); font-size: 12px; }
				.customer-list, .group-list, .student-list { max-height: 68vh; overflow: auto; }
				.invoice-row {
					position: relative;
					display: grid;
					gap: 6px;
					padding: 12px;
					border-bottom: 1px solid #edf1f5;
					background: #fff;
					transition: background .12s ease, box-shadow .12s ease, border-color .12s ease;
				}
				.customer-row, .group-row { cursor: pointer; }
				.invoice-row:hover { background: #fbfdff; }
				.invoice-row.active {
					background: var(--invoice-active);
					box-shadow: inset 3px 0 0 var(--invoice-active-border);
				}
				.group-row.selected, .student-row.selected { background: #f0fbf5; }
				.row-main { display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }
				.row-title { font-weight: 700; color: var(--invoice-text); min-width: 0; overflow-wrap: anywhere; }
				.row-meta { display: flex; flex-wrap: wrap; gap: 8px; color: var(--invoice-muted); font-size: 12px; }
				.count-badge {
					border-radius: 999px;
					padding: 2px 9px;
					font-size: 12px;
					background: var(--invoice-green-bg);
					color: var(--invoice-green);
					font-weight: 700;
					white-space: nowrap;
				}
				.select-wrap { display: flex; align-items: center; gap: 7px; margin: 0; color: var(--invoice-text); font-weight: 500; white-space: nowrap; }
				.group-row { grid-template-columns: 24px 1fr; align-items: start; }
				.group-check, .student-check, .select-wrap input { cursor: pointer; }
				.group-check, .student-check { margin-top: 3px; }
				.student-row { grid-template-columns: 24px 1fr; align-items: start; }
				.status-pill { border-radius: 999px; padding: 2px 9px; font-size: 12px; font-weight: 700; white-space: nowrap; }
				.status-pending { background: var(--invoice-green-bg); color: var(--invoice-green); }
				.status-process { background: var(--invoice-orange-bg); color: var(--invoice-orange); }
				.status-invoiced { background: var(--invoice-blue-bg); color: var(--invoice-blue); }
				.empty-state { padding: 34px 12px; text-align: center; color: var(--invoice-muted); }
				@media (max-width: 1200px) {
					.invoice-toolbar, .invoice-workspace { grid-template-columns: 1fr; }
					.invoice-actionbar { align-items: flex-start; flex-direction: column; }
					.action-buttons { justify-content: flex-start; }
					.customer-list, .group-list, .student-list { max-height: none; }
				}
			</style>
		`);
	}

	bind_events() {
		this.$root.on("click", ".customer-row", (event) => {
			const next_customer_index = cint($(event.currentTarget).data("customerIndex"));
			if (next_customer_index !== this.active_customer_index) {
				this.selected_rows.clear();
			}
			this.active_customer_index = next_customer_index;
			this.active_group_index = 0;
			this.render();
		});

		this.$root.on("click", ".group-row", (event) => {
			if ($(event.target).is("input")) return;
			this.active_group_index = cint($(event.currentTarget).data("groupIndex"));
			this.render_groups();
			this.render_students();
		});

		this.$root.on("change", ".group-check", (event) => {
			const group_index = cint($(event.currentTarget).data("groupIndex"));
			this.set_group_selection(this.active_customer.groups[group_index], event.currentTarget.checked);
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("change", ".student-check", (event) => {
			const row_name = $(event.currentTarget).data("row");
			if (event.currentTarget.checked) {
				this.selected_rows.add(row_name);
			} else {
				this.selected_rows.delete(row_name);
			}
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("change", ".select-all-students", (event) => {
			this.set_group_selection(this.active_group, event.currentTarget.checked);
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("change", ".select-all-groups", (event) => {
			this.set_customer_selection(this.active_customer, event.currentTarget.checked);
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("click", ".select-customer-pending", () => {
			this.set_customer_selection(this.active_customer, true);
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("click", ".select-visible-pending", () => {
			this.customers.forEach((customer) => this.set_customer_selection(customer, true));
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("change", ".show-all-customers", () => {
			this.refresh();
		});

		this.$root.on("click", ".clear-selection", () => {
			this.selected_rows.clear();
			this.render_groups();
			this.render_students();
			this.update_selection_bar();
		});

		this.$root.on("click", ".create-invoice", () => this.create_invoice());
	}

	get active_customer() {
		return this.customers[this.active_customer_index] || null;
	}

	get active_group() {
		return this.active_customer?.groups?.[this.active_group_index] || null;
	}

	filters() {
		return {
			customer: this.customer_filter.get_value(),
			from_date: this.from_date_filter.get_value(),
			to_date: this.to_date_filter.get_value(),
			show_all_customers: this.$root?.find(".show-all-customers").prop("checked") ? 1 : 0,
		};
	}

	refresh() {
		this.selected_rows.clear();
		this.active_customer_index = 0;
		this.active_group_index = 0;
		this.$root.find(".customer-list").html(`<div class="empty-state">${__("Loading")}</div>`);
		this.$root.find(".group-list, .student-list").html("");
		frappe.call({
			method: "numerouno.numerouno.page.invoiced_creation.invoiced_creation.get_data",
			args: { filters: this.filters() },
			callback: (r) => {
				this.customers = r.message?.customers || [];
				this.render();
			},
		});
	}

	render() {
		this.render_stats();
		this.render_customers();
		this.render_groups();
		this.render_students();
		this.update_selection_bar();
	}

	render_stats() {
		const totals = this.customers.reduce((acc, row) => {
			acc.pending += row.pending_students || 0;
			acc.process += row.in_process_students || 0;
			acc.invoiced += row.invoiced_students || 0;
			return acc;
		}, { pending: 0, process: 0, invoiced: 0 });
		this.$root.find('[data-stat="customers"] span').text(this.customers.length);
		this.$root.find('[data-stat="pending"] span').text(totals.pending);
		this.$root.find('[data-stat="process"] span').text(totals.process);
		this.$root.find('[data-stat="invoiced"] span').text(totals.invoiced);
	}

	render_customers() {
		const html = this.customers.map((row, index) => `
			<div class="invoice-row customer-row ${this.active_customer_index === index ? "active" : ""}" data-customer-index="${index}">
				<div class="row-main">
					<div class="row-title">${this.escape(row.customer)}</div>
					<div class="count-badge">${row.pending_students || 0}</div>
				</div>
				<div class="row-meta">
					<span>${__("Groups")}: ${row.pending_groups || 0}</span>
					<span>${__("In Process")}: ${row.in_process_students || 0}</span>
					<span>${__("Invoiced")}: ${row.invoiced_students || 0}</span>
				</div>
			</div>
		`).join("");
		this.$root.find(".customer-list").html(html || `<div class="empty-state">${__("No pending customers")}</div>`);
	}

	render_groups() {
		const groups = this.active_customer?.groups || [];
		const html = groups.map((row, index) => {
			const pending = this.pending_students_for_group(row);
			const selected = pending.length > 0 && pending.every((student) => this.selected_rows.has(student.row_name));
			const partial = pending.some((student) => this.selected_rows.has(student.row_name)) && !selected;
			return `
				<div class="invoice-row group-row ${this.active_group_index === index ? "active" : ""} ${selected || partial ? "selected" : ""}" data-group-index="${index}">
					<input type="checkbox" class="group-check" data-group-index="${index}" ${selected ? "checked" : ""} ${pending.length ? "" : "disabled"}>
					<div>
						<div class="row-main">
							<div class="row-title">${this.escape(row.student_group_name || row.student_group)}</div>
							<div class="count-badge">${row.pending_students || 0}</div>
						</div>
						<div class="row-meta">
							<span>${this.escape(row.course || "")}</span>
							<span>${__("Selected")}: ${pending.filter((student) => this.selected_rows.has(student.row_name)).length}</span>
							<span>${__("Invoiced")}: ${row.invoiced_students || 0}</span>
						</div>
					</div>
				</div>
			`;
		}).join("");
		this.$root.find(".group-list").html(html || `<div class="empty-state">${__("No student groups")}</div>`);
		this.$root.find(".group-summary").text(this.active_customer ?
			__("{0} groups, {1} pending students", [groups.length, this.active_customer.pending_students || 0]) :
			__("choose a customer"));

		const customer_pending = this.pending_students_for_customer(this.active_customer);
		const all_selected = customer_pending.length > 0 && customer_pending.every((student) => this.selected_rows.has(student.row_name));
		this.$root.find(".select-all-groups")
			.prop("disabled", customer_pending.length === 0)
			.prop("checked", all_selected);
	}

	render_students() {
		const selected_groups = this.selected_groups_for_customer(this.active_customer);
		const showing_selected_groups = selected_groups.length > 1;
		const students = showing_selected_groups ?
			selected_groups.flatMap((group) => this.pending_students_for_group(group)) :
			(this.active_group?.students || []);
		const html = students.map((student) => {
			const disabled = student.is_pending ? "" : "disabled";
			const checked = this.selected_rows.has(student.row_name) ? "checked" : "";
			const selected = checked ? "selected" : "";
			const status_class = student.invoice_status === "Pending" ? "status-pending" :
				student.invoice_status === "In Process" ? "status-process" : "status-invoiced";
			return `
				<div class="invoice-row student-row ${selected}">
					<input type="checkbox" class="student-check" data-row="${this.escape(student.row_name)}" ${checked} ${disabled}>
					<div>
						<div class="row-main">
							<div class="row-title">${this.escape(student.student_name || student.student)}</div>
							<div class="status-pill ${status_class}">${this.escape(student.invoice_status)}</div>
						</div>
						<div class="row-meta">
							<span>${showing_selected_groups ? this.escape(student.student_group || "") : ""}</span>
							<span>${this.escape(student.student || "")}</span>
							<span>${student.start_date ? frappe.datetime.str_to_user(student.start_date) : ""}</span>
							<span>${this.escape(student.customer_purchase_order || "")}</span>
						</div>
					</div>
				</div>
			`;
		}).join("");
		this.$root.find(".student-list").html(html || `<div class="empty-state">${__("No students")}</div>`);

		const pending = showing_selected_groups ? students : this.pending_students_for_group(this.active_group);
		const all_selected = pending.length > 0 && pending.every((student) => this.selected_rows.has(student.row_name));
		this.$root.find(".select-all-students")
			.prop("disabled", pending.length === 0)
			.prop("checked", all_selected);
		this.$root.find(".student-select-wrap span").text(showing_selected_groups ? __("Shown Students") : __("All Students"));
		this.$root.find(".student-summary").text(showing_selected_groups ?
			__("{0} selected groups, {1} selected students shown", [selected_groups.length, students.length]) :
			(this.active_group ?
				__("{0} pending, {1} selected", [
				pending.length,
				pending.filter((student) => this.selected_rows.has(student.row_name)).length,
				]) :
				__("choose a group")));
	}

	pending_students_for_group(group) {
		return (group?.students || []).filter((student) => student.is_pending);
	}

	pending_students_for_customer(customer) {
		return (customer?.groups || []).flatMap((group) => this.pending_students_for_group(group));
	}

	selected_groups_for_customer(customer) {
		return (customer?.groups || []).filter((group) =>
			this.pending_students_for_group(group).some((student) => this.selected_rows.has(student.row_name))
		);
	}

	set_group_selection(group, checked) {
		this.pending_students_for_group(group).forEach((student) => {
			if (checked) {
				this.selected_rows.add(student.row_name);
			} else {
				this.selected_rows.delete(student.row_name);
			}
		});
	}

	set_customer_selection(customer, checked) {
		this.pending_students_for_customer(customer).forEach((student) => {
			if (checked) {
				this.selected_rows.add(student.row_name);
			} else {
				this.selected_rows.delete(student.row_name);
			}
		});
	}

	update_selection_bar() {
		const selected_count = this.selected_rows.size;
		const groups_selected = new Set();
		const customers_selected = new Set();
		this.customers.forEach((customer) => {
			this.pending_students_for_customer(customer).forEach((student) => {
				if (this.selected_rows.has(student.row_name)) {
					groups_selected.add(student.student_group);
					customers_selected.add(customer.customer);
				}
			});
		});
		this.$root.find(".selected-summary").text(selected_count ?
			__("{0} students selected across {1} customers and {2} student groups", [
				selected_count,
				customers_selected.size,
				groups_selected.size,
			]) :
			__("No pending students selected"));
		const visible_pending = this.customers.some((customer) => customer.pending_students);
		this.$root.find(".create-invoice").prop("disabled", selected_count === 0);
		this.$root.find(".clear-selection").prop("disabled", selected_count === 0);
		this.$root.find(".select-customer-pending").prop("disabled", !this.active_customer || !this.active_customer.pending_students);
		this.$root.find(".select-visible-pending").prop("disabled", !visible_pending);
	}

	create_invoice() {
		if (!this.selected_rows.size) return;

		const customer_count = this.selected_customer_count();
		const selected_count = this.selected_rows.size;
		const message = customer_count > 1 ?
			__("This will create {0} draft Sales Invoices for {1} selected students across {2} customers. Continue?", [
				customer_count,
				selected_count,
				customer_count,
			]) :
			__("Create 1 draft Sales Invoice for {0} selected student(s)?", [selected_count]);

		frappe.confirm(message, () => {
			frappe.call({
				method: "numerouno.numerouno.page.invoiced_creation.invoiced_creation.create_invoices",
				args: {
					row_names: Array.from(this.selected_rows),
				},
				freeze: true,
				freeze_message: __("Creating Invoice"),
				callback: (r) => {
					const invoices = r.message?.invoices || [];
					if (!invoices.length) return;
					frappe.show_alert({
						message: __("{0} Sales Invoice draft(s) created", [invoices.length]),
						indicator: "green",
					});
					this.refresh();
					if (invoices.length === 1) {
						frappe.set_route("Form", "Sales Invoice", invoices[0].sales_invoice);
					} else {
						frappe.set_route("List", "Sales Invoice");
					}
				},
			});
		});
	}

	selected_customer_count() {
		const selected_customers = new Set();
		this.customers.forEach((customer) => {
			this.pending_students_for_customer(customer).forEach((student) => {
				if (this.selected_rows.has(student.row_name)) {
					selected_customers.add(customer.customer);
				}
			});
		});
		return selected_customers.size;
	}

	escape(value) {
		return frappe.utils.escape_html(value == null ? "" : String(value));
	}
}
