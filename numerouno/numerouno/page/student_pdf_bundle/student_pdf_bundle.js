frappe.pages["student-pdf-bundle"].on_page_load = function (wrapper) {
	if (wrapper.student_pdf_bundle) {
		return;
	}

	if (!$("#student-pdf-bundle-css").length) {
		$(
			'<link id="student-pdf-bundle-css" rel="stylesheet" type="text/css" href="/assets/numerouno/css/student_pdf_bundle.css">'
		).appendTo("head");
	}

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Student PDF Bundle"),
		single_column: true,
	});

	page.main.addClass("student-pdf-bundle-page");
	wrapper.student_pdf_bundle = new StudentPdfBundlePage(page);
};

class StudentPdfBundlePage {
	constructor(page) {
		this.page = page;
		this.items = [];
		this.selected = new Set();
		this.make_filters();
		this.make_layout();
		this.bind_events();
	}

	make_filters() {
		this.student_group_field = this.page.add_field({
			fieldname: "student_group",
			label: __("Student Group"),
			fieldtype: "Link",
			options: "Student Group",
			change: () => {
				this.student_field.set_value("");
				this.clear_results();
			},
		});

		this.student_field = this.page.add_field({
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student",
			get_query: () => {
				const student_group = this.student_group_field.get_value();
				if (!student_group) {
					return {};
				}
				return {
					query: "numerouno.numerouno.page.student_pdf_bundle.student_pdf_bundle.student_query",
					filters: { student_group },
				};
			},
			change: () => this.clear_results(),
		});

		this.page.set_primary_action(__("Find PDFs"), () => this.find_pdfs(), "search");
	}

	make_layout() {
		this.$root = $(`
			<div class="spb-root">
				<div class="spb-help">
					${__(
						"Select a Student Group, a Student, or both. We will list every printable PDF linked to your selection."
					)}
				</div>
				<div class="spb-toolbar">
					<div class="spb-stats">
						<span class="spb-stat"><b class="spb-count">0</b> ${__("PDFs found")}</span>
						<span class="spb-stat"><b class="spb-selected">0</b> ${__("selected")}</span>
					</div>
					<div class="spb-actions">
						<button type="button" class="btn btn-default btn-sm spb-select-all">${__("Select All")}</button>
						<button type="button" class="btn btn-default btn-sm spb-clear-all">${__("Clear")}</button>
						<button type="button" class="btn btn-primary btn-sm spb-download-merge" disabled>${__(
							"Download Merged PDF"
						)}</button>
						<button type="button" class="btn btn-default btn-sm spb-download-zip" disabled>${__(
							"Download ZIP"
						)}</button>
					</div>
				</div>
				<div class="spb-results"></div>
			</div>
		`).appendTo(this.page.main);
	}

	bind_events() {
		this.$root.on("click", ".spb-select-all", () => this.select_all(true));
		this.$root.on("click", ".spb-clear-all", () => this.select_all(false));
		this.$root.on("change", ".spb-check", (e) => {
			const id = $(e.currentTarget).data("id");
			if (e.currentTarget.checked) {
				this.selected.add(id);
			} else {
				this.selected.delete(id);
			}
			this.update_counts();
		});
		this.$root.on("click", ".spb-open-print", (e) => {
			e.preventDefault();
			const $row = $(e.currentTarget).closest(".spb-row");
			frappe.set_route("print", $row.data("doctype"), $row.data("name"));
		});
		this.$root.on("click", ".spb-download-merge", () => this.download(true));
		this.$root.on("click", ".spb-download-zip", () => this.download(false));
	}

	clear_results() {
		this.items = [];
		this.selected.clear();
		this.render_results();
		this.update_counts();
	}

	find_pdfs() {
		const student_group = this.student_group_field.get_value();
		const student = this.student_field.get_value();
		if (!student_group && !student) {
			frappe.msgprint(__("Select a Student Group and/or Student."));
			return;
		}

		frappe.call({
			method: "numerouno.numerouno.page.student_pdf_bundle.student_pdf_bundle.find_pdfs",
			args: { student_group, student },
			freeze: true,
			freeze_message: __("Finding PDFs..."),
			callback: (r) => {
				this.items = r.message?.items || [];
				this.selected = new Set(this.items.map((row) => row.id));
				this.render_results();
				this.update_counts();
				if (!this.items.length) {
					frappe.show_alert({
						message: __("No PDFs found for this selection."),
						indicator: "orange",
					});
				}
			},
		});
	}

	render_results() {
		const $results = this.$root.find(".spb-results");
		if (!this.items.length) {
			$results.html(`<div class="spb-empty">${__("Use Find PDFs to load printable documents.")}</div>`);
			return;
		}

		const groups = {};
		this.items.forEach((item) => {
			groups[item.category] = groups[item.category] || [];
			groups[item.category].push(item);
		});

		const html = Object.keys(groups)
			.map((category) => {
				const rows = groups[category]
					.map(
						(item) => `
					<div class="spb-row" data-id="${frappe.utils.escape_html(item.id)}"
						data-doctype="${frappe.utils.escape_html(item.doctype)}"
						data-name="${frappe.utils.escape_html(item.name)}">
						<label class="spb-row-check">
							<input type="checkbox" class="spb-check" data-id="${frappe.utils.escape_html(item.id)}"
								${this.selected.has(item.id) ? "checked" : ""}>
						</label>
						<div class="spb-row-body">
							<div class="spb-row-title">${frappe.utils.escape_html(item.title)}</div>
							<div class="spb-row-meta">
								<span>${frappe.utils.escape_html(item.label)}</span>
								<span>${frappe.utils.escape_html(item.name)}</span>
								${item.student_name ? `<span>${frappe.utils.escape_html(item.student_name)}</span>` : ""}
								${item.student_group ? `<span>${frappe.utils.escape_html(item.student_group)}</span>` : ""}
								<span class="spb-status">${item.docstatus ? __("Submitted") : __("Draft")}</span>
							</div>
						</div>
						<button type="button" class="btn btn-default btn-xs spb-open-print">${__("Preview")}</button>
					</div>`
					)
					.join("");
				return `
					<div class="spb-group">
						<div class="spb-group-title">${frappe.utils.escape_html(category)}</div>
						${rows}
					</div>`;
			})
			.join("");

		$results.html(html);
	}

	select_all(on) {
		if (on) {
			this.selected = new Set(this.items.map((row) => row.id));
		} else {
			this.selected.clear();
		}
		this.$root.find(".spb-check").prop("checked", on);
		this.update_counts();
	}

	update_counts() {
		this.$root.find(".spb-count").text(this.items.length);
		this.$root.find(".spb-selected").text(this.selected.size);
		const enabled = this.selected.size > 0;
		this.$root.find(".spb-download-merge, .spb-download-zip").prop("disabled", !enabled);
	}

	download(merge) {
		const selected_items = this.items.filter((row) => this.selected.has(row.id));
		if (!selected_items.length) {
			frappe.msgprint(__("Select at least one PDF."));
			return;
		}

		frappe.call({
			method: "numerouno.numerouno.page.student_pdf_bundle.student_pdf_bundle.prepare_download",
			args: {
				items: selected_items,
				merge: merge ? 1 : 0,
			},
			freeze: true,
			freeze_message: __("Preparing download..."),
			callback: (r) => {
				const key = r.message;
				if (!key) {
					frappe.msgprint(__("Could not prepare download."));
					return;
				}
				open_url_post(
					"/api/method/numerouno.numerouno.page.student_pdf_bundle.student_pdf_bundle.download_pdfs",
					{ key }
				);
			},
		});
	}
}
