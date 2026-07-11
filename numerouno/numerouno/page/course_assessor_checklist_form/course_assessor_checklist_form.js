frappe.pages["course-assessor-checklist-form"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Course Assessor Checklist"),
		single_column: true,
	});

	page.main.addClass("course-assessor-checklist-page");
	wrapper.course_assessor_checklist = new CourseAssessorChecklist(page);
};

frappe.pages["course-assessor-checklist-form"].on_page_show = function (wrapper) {
	wrapper.course_assessor_checklist?.resolve_route_and_load();
};

const CAC_CHECKLIST_TYPES = [
	"Basic H2S",
	"BOSIET EBS",
	"TBOSIET",
	"FOET EBS",
	"T FOET",
	"HUET EBS",
	"THUET",
	"Gas Monitor",
	"AGT",
	"TSbB Initial",
	"TSbB Further",
];

class CourseAssessorChecklist {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.saving = false;
		this.loading_key = null;
		this.active_tab = "All";
		this.list_offset = 0;
		this.list_page_size = 50;
		this.type_counts = {};

		this.$root = $('<div class="cac-root"></div>').appendTo(this.page.main);
		this.make_actions();
		this.resolve_route_and_load();
	}

	make_actions() {
		this.page.clear_inner_toolbar();
		this.page.set_primary_action(__("New Checklist"), () => this.open_create_dialog());
		this.page.add_inner_button(__("Refresh List"), () => this.show_list(), __("Actions"));
	}

	make_form_actions() {
		this.page.clear_inner_toolbar();
		this.page.set_primary_action(__("Save"), () => this.save());
		this.page.add_inner_button(__("Back to List"), () => {
			this.loading_key = null;
			frappe.set_route("course-assessor-checklist-form");
		});
		this.page.add_inner_button(__("Print"), () => this.print_doc(), __("Actions"));
		this.page.add_inner_button(__("Submit"), () => this.submit_doc(), __("Actions"));
		this.page.add_inner_button(__("Populate Learners"), () => this.populate_learners(), __("Actions"));
		this.page.add_inner_button(__("ERP Form"), () => this.open_erp_form(), __("Actions"));
		this.page.add_inner_button(__("New"), () => this.open_create_dialog(), __("Actions"));
	}

	resolve_route_and_load() {
		const route = frappe.get_route() || [];
		const docname = (route[1] || frappe.route_options?.name || frappe.utils.get_query_params().name || "").trim();
		const checklist_type = (
			frappe.route_options?.checklist_type || frappe.utils.get_query_params().checklist_type || ""
		).trim();
		const student_group =
			frappe.route_options?.student_group || frappe.utils.get_query_params().student_group || null;

		// Consume one-shot route options so Back to List does not reopen a new form.
		if (frappe.route_options) {
			delete frappe.route_options.checklist_type;
			delete frappe.route_options.student_group;
			delete frappe.route_options.name;
		}

		const load_key = docname || `new:${checklist_type}:${student_group || ""}`;
		if (this.loading_key === load_key && this.doc && (docname ? this.doc.name === docname : !this.doc.name)) {
			return;
		}
		this.loading_key = load_key;

		if (docname) {
			this.fetch_form({ docname });
			return;
		}

		if (checklist_type) {
			this.fetch_form({ checklist_type, student_group });
			return;
		}

		this.show_list();
	}

	show_list(append = false) {
		this.doc = null;
		this.loading_key = "list";
		this.make_actions();
		this.page.set_title(__("Course Assessor Checklist"));

		if (!append) {
			this.list_offset = 0;
			this.$root.html(`
				<div class="cac-portal">
					<div class="cac-portal-header">
						<div>
							<h3>${__("Course Assessor Checklist")}</h3>
							<p>${__("NUTC-P14-F01 series — browse by course type, then open or create a checklist.")}</p>
						</div>
						<button type="button" class="cac-btn cac-btn-primary cac-new-btn">${__("New Checklist")}</button>
					</div>
					<div class="cac-tabs"></div>
					<div class="cac-panel">
						<table class="cac-table">
							<thead>
								<tr>
									<th>${__("Checklist")}</th>
									<th>${__("Type")}</th>
									<th>${__("Student Group")}</th>
									<th>${__("Date")}</th>
									<th>${__("Status")}</th>
									<th>${__("Modified")}</th>
									<th>${__("Action")}</th>
								</tr>
							</thead>
							<tbody class="cac-list-body">
								<tr><td colspan="7" class="cac-empty">${__("Loading...")}</td></tr>
							</tbody>
						</table>
						<div class="cac-load-more-wrap" hidden>
							<button type="button" class="cac-btn cac-btn-ghost cac-load-more">${__("Load more")}</button>
						</div>
					</div>
				</div>
			`);
			this.$root.find(".cac-new-btn").on("click", () => this.open_create_dialog());
			this.$root.find(".cac-load-more").on("click", () => {
				this.list_offset += this.list_page_size;
				this.show_list(true);
			});
		}

		frappe.call({
			method:
				"numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.get_checklist_list",
			args: {
				checklist_type: this.active_tab === "All" ? null : this.active_tab,
				limit: this.list_page_size,
				offset: this.list_offset,
			},
			callback: (r) => {
				if (r.exc) return;
				const msg = r.message || {};
				this.type_counts = msg.type_counts || {};
				this.render_tabs(msg.checklist_types || CAC_CHECKLIST_TYPES, msg.total || 0);
				this.render_list_rows(msg.records || [], append);
				this.$root.find(".cac-load-more-wrap").toggle(!!msg.has_more);
			},
			error: () => {
				this.render_list_rows([], false);
			},
		});
	}

	render_tabs(types, total) {
		const tabs = ["All", ...types];
		const html = tabs
			.map((tab) => {
				const count = tab === "All" ? total : this.type_counts[tab] || 0;
				const active = tab === this.active_tab ? "active" : "";
				return `<button type="button" class="cac-tab ${active}" data-tab="${frappe.utils.escape_html(tab)}">
					${frappe.utils.escape_html(tab)}
					<span class="cac-tab-count">(${count})</span>
				</button>`;
			})
			.join("");
		this.$root.find(".cac-tabs").html(html);
		this.$root.find(".cac-tab").on("click", (e) => {
			const tab = $(e.currentTarget).data("tab");
			if (!tab || tab === this.active_tab) return;
			this.active_tab = tab;
			this.show_list(false);
		});
	}

	render_list_rows(records, append) {
		const $body = this.$root.find(".cac-list-body");
		if (!append) $body.empty();

		if (!records.length && !append) {
			$body.html(`
				<tr>
					<td colspan="7" class="cac-empty">
						${__("No checklists found for this course type.")}
						<br><br>
						<button type="button" class="cac-btn cac-btn-primary cac-empty-new">${__("Create New")}</button>
					</td>
				</tr>
			`);
			$body.find(".cac-empty-new").on("click", () =>
				this.open_create_dialog({
					checklist_type: this.active_tab !== "All" ? this.active_tab : "",
				})
			);
			return;
		}

		records.forEach((row) => $body.append(this.render_list_row(row)));
		$body.find(".cac-open-btn").off("click").on("click", (e) => {
			e.preventDefault();
			const name = $(e.currentTarget).data("name");
			if (name) {
				this.loading_key = null;
				frappe.set_route("course-assessor-checklist-form", name);
			}
		});
	}

	render_list_row(row) {
		const dateLabel = row.assessment_date ? frappe.datetime.str_to_user(row.assessment_date) : "-";
		const modifiedLabel = row.modified ? frappe.datetime.str_to_user(row.modified) : "-";
		const formCode = row.form_code
			? `<div class="cac-data-meta">${frappe.utils.escape_html(row.form_code)}</div>`
			: "";
		const status = this.status_pill(row.docstatus);
		return `
			<tr>
				<td>
					<div class="cac-data-title">
						<a href="#" class="cac-open-btn" data-name="${frappe.utils.escape_html(row.name || "")}">
							${frappe.utils.escape_html(row.name || "-")}
						</a>
					</div>
					${formCode}
				</td>
				<td><div class="cac-data-title">${frappe.utils.escape_html(row.checklist_type || "-")}</div></td>
				<td><div class="cac-data-title">${frappe.utils.escape_html(row.student_group || "-")}</div></td>
				<td><div class="cac-data-title">${frappe.utils.escape_html(dateLabel)}</div></td>
				<td>${status}</td>
				<td><div class="cac-data-title">${frappe.utils.escape_html(modifiedLabel)}</div></td>
				<td>
					<div class="cac-row-actions">
						<a href="#" class="cac-btn cac-btn-primary cac-open-btn" data-name="${frappe.utils.escape_html(row.name || "")}">${__("Open")}</a>
						<a class="cac-btn cac-btn-ghost" href="/app/assessor-checklist/${frappe.utils.escape_html(row.name || "")}">${__("ERP View")}</a>
					</div>
				</td>
			</tr>
		`;
	}

	status_pill(docstatus) {
		const ds = cint(docstatus);
		if (ds === 1) return `<span class="cac-status cac-status-submitted">${__("Submitted")}</span>`;
		if (ds === 2) return `<span class="cac-status cac-status-cancelled">${__("Cancelled")}</span>`;
		return `<span class="cac-status cac-status-draft">${__("Draft")}</span>`;
	}

	open_create_dialog(defaults = {}) {
		const defaultType =
			defaults.checklist_type || (this.active_tab !== "All" ? this.active_tab : "TBOSIET");
		const dialog = new frappe.ui.Dialog({
			title: __("Create Course Assessor Checklist"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "checklist_type",
					label: __("Checklist Type / Course"),
					options: CAC_CHECKLIST_TYPES.join("\n"),
					default: defaultType,
					reqd: 1,
				},
				{
					fieldtype: "Link",
					fieldname: "student_group",
					label: __("Student Group"),
					options: "Student Group",
					default: defaults.student_group || "",
				},
				{
					fieldtype: "HTML",
					fieldname: "help_html",
					options: `<p class="text-muted" style="margin:0;">${__(
						"Opens the official NUTC-P14-F01 Word-style checklist for this course type."
					)}</p>`,
				},
			],
			primary_action_label: __("Open Form"),
			primary_action: (values) => {
				if (!values.checklist_type) {
					frappe.msgprint(__("Select a Checklist Type"));
					return;
				}
				dialog.hide();
				this.loading_key = null;
				frappe.route_options = {
					checklist_type: values.checklist_type,
					student_group: values.student_group || null,
				};
				// Clear route docname if any, then load new form
				if ((frappe.get_route() || [])[1]) {
					frappe.set_route("course-assessor-checklist-form");
					setTimeout(() => {
						this.fetch_form({
							checklist_type: values.checklist_type,
							student_group: values.student_group || null,
						});
					}, 50);
				} else {
					this.fetch_form({
						checklist_type: values.checklist_type,
						student_group: values.student_group || null,
					});
				}
			},
		});
		dialog.show();
	}

	fetch_form(args) {
		const load_key = args.docname || `new:${args.checklist_type || ""}:${args.student_group || ""}`;
		this.loading_key = load_key;
		this.make_form_actions();

		frappe.call({
			method:
				"numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.get_form_html",
			args,
			freeze: true,
			callback: (r) => {
				if (r.exc) {
					this.loading_key = null;
					return;
				}
				this.doc = r.message.doc;
				this.render(r.message.html);
				const title = this.doc.name
					? `${this.doc.checklist_type} (${this.doc.name})`
					: this.doc.checklist_type;
				this.page.set_title(`${__("Course Assessor Checklist")} — ${title}`);
			},
			error: () => {
				this.loading_key = null;
			},
		});
	}

	render(html) {
		if (!this.doc) return;

		this.$root.html(`
			<div class="cac-toolbar-bar">
				<p class="cac-toolbar-note">
					<strong>${frappe.utils.escape_html(this.doc.checklist_type || "")}</strong>
					${this.doc.form_code ? ` — ${frappe.utils.escape_html(this.doc.form_code)}` : ""}
					<br>${__("Click a cell, then use C / N / Space. Arrow keys move between marks.")}
				</p>
				<div class="cac-toolbar-actions">
					<button type="button" class="cac-btn cac-btn-ghost cac-back-list">${__("Back to List")}</button>
				</div>
			</div>
			<div class="cac-form-meta-panel">
				<div class="cac-header-fields">
					<div class="cac-field cac-field-date">
						<label class="cac-field-label">${__("Assessment Date")}</label>
						<input type="date" class="cac-date-input cac-root-field" data-root="assessment_date" value="${this.doc.assessment_date || ""}">
					</div>
					<div class="cac-field cac-field-group">
						<label class="cac-field-label">${__("Student Group")}</label>
						<div class="cac-student-group-wrap"></div>
					</div>
				</div>
				<div class="cac-entry-toolbar">
					<button type="button" class="cac-btn cac-btn-primary cac-fill-c">${__("Fill empty with C")}</button>
					<button type="button" class="cac-btn cac-btn-ghost cac-clear-marks">${__("Clear all marks")}</button>
					<span class="cac-entry-hint">
						${__("Keys")}: <kbd>↑</kbd><kbd>↓</kbd><kbd>←</kbd><kbd>→</kbd>
						&nbsp;·&nbsp; <kbd>C</kbd> Competent
						&nbsp;·&nbsp; <kbd>N</kbd> NYC
						&nbsp;·&nbsp; <kbd>Space</kbd> Clear
						&nbsp;·&nbsp; <kbd>Enter</kbd> Next row
					</span>
				</div>
			</div>
			<div class="cac-doc-wrap">
				<div class="cac-doc">${html}</div>
			</div>
		`);

		this.$root.find(".cac-back-list").on("click", () => {
			this.loading_key = null;
			frappe.set_route("course-assessor-checklist-form");
		});
		this.$root.find(".cac-fill-c").on("click", () => this.bulk_set_marks("C", true));
		this.$root.find(".cac-clear-marks").on("click", () => this.bulk_set_marks("", false));

		const group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Student Group",
				fieldname: "student_group",
				label: __("Student Group"),
				only_input: 1,
				change: () => {
					this.doc.student_group = group_field.get_value();
				},
			},
			parent: this.$root.find(".cac-student-group-wrap"),
			render_input: true,
			only_input: true,
		});
		group_field.make();
		group_field.set_value(this.doc.student_group || "");
		group_field.refresh();
		this.$root.find(".cac-student-group-wrap .clearfix, .cac-student-group-wrap .control-label").remove();
		this.student_group_field = group_field;

		this.enhance_editable();
		this.init_signature_pads();
		this.bind_mark_keyboard();
		this.apply_readonly_state();
	}

	enhance_editable() {
		const d = this.doc;
		const $doc = this.$root.find(".cac-doc");
		const outcome_count = (d.outcomes || []).length;

		$doc.find(".acl-grid").addClass("cac-entry-grid");

		if (d.checklist_type === "Basic H2S") {
			$doc.find(".acl-variants").html(`
				<label><input type="checkbox" class="cac-variant-check" data-root="variant_9014" ${d.variant_9014 ? "checked" : ""}> 9014</label>
				&nbsp;
				<label><input type="checkbox" class="cac-variant-check" data-root="variant_9014_a" ${d.variant_9014_a ? "checked" : ""}> 9014-A</label>
				&nbsp;
				<label><input type="checkbox" class="cac-variant-check" data-root="variant_9014_b" ${d.variant_9014_b ? "checked" : ""}> 9014-B</label>
			`);
		}

		if (["BOSIET EBS", "FOET EBS", "HUET EBS"].includes(d.checklist_type)) {
			$doc.find(".acl-ebs, .acl-header").append(`
				<div class="acl-ebs cac-ebs-field" style="margin-top:4px;">
					EBS NO: <input type="text" class="cac-cell-input cac-root-field" data-root="ebs_no" value="${frappe.utils.escape_html(d.ebs_no || "")}">
				</div>
			`);
		}

		$doc.find(".acl-grid tr").each((_, tr) => {
			if ($(tr).hasClass("acl-grid-head")) {
				$(tr).find(".col-outcome").each((col_idx, th) => {
					const $th = $(th);
					$th.attr("data-col", col_idx);
					$th.append(
						`<button type="button" class="cac-col-fill" data-col="${col_idx}" title="${__("Fill column with C")}">C↓</button>`
					);
				});
				return;
			}
			const learner_idx = cint($(tr).find(".col-no").text().trim()) - 1;
			if (learner_idx < 0 || learner_idx > 15) return;
			const row = (d.learners || [])[learner_idx] || {};
			$(tr).attr("data-row", learner_idx);

			$(tr).find(".col-name").html(
				this.text_input("learners", learner_idx, "learner_name", row.learner_name)
			);

			$(tr).find(".col-result").each((col_idx, cell) => {
				const field = `result_${col_idx + 1}`;
				if (col_idx + 1 > outcome_count) return;
				$(cell)
					.attr("data-row", learner_idx)
					.attr("data-col", col_idx)
					.html(this.result_mark("learners", learner_idx, field, row[field], col_idx));
			});
		});

		$doc.find(".cac-col-fill").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const col = cint($(e.currentTarget).data("col"));
			this.fill_column(col, "C");
		});

		let assessor_idx = -1;
		$doc.find(".acl-assessors tr").each((_, tr) => {
			if ($(tr).find("th").length) return;
			assessor_idx += 1;
			const row = (d.assessors || [])[assessor_idx] || {};
			const cells = $(tr).find("td");
			if (!cells.length) return;
			$(cells[1]).html(this.text_input("assessors", assessor_idx, "assessor_name", row.assessor_name));
			$(cells[2]).html(this.text_input("assessors", assessor_idx, "module", row.module));
			$(cells[3]).html(this.text_input("assessors", assessor_idx, "description", row.description));
			$(cells[4]).html(this.signature_cell("assessors", assessor_idx, "signature", row.signature));
			$(cells[5]).html(this.date_input_table("assessors", assessor_idx, "assessor_date", row.assessor_date));
			$(cells[6]).html(this.text_input("assessors", assessor_idx, "day", row.day));
			$(cells[7]).html(this.text_input("assessors", assessor_idx, "time_ampm", row.time_ampm));
		});

		const $remarks = $doc.find(".acl-remarks");
		if ($remarks.length) {
			$remarks.html(`<strong>Remarks:</strong><br><textarea class="cac-remarks-input cac-root-field" data-root="remarks">${frappe.utils.escape_html(d.remarks || "")}</textarea>`);
		} else {
			$doc.find(".acl-grid").after(`
				<p class="acl-remarks"><strong>Remarks:</strong><br><textarea class="cac-remarks-input cac-root-field" data-root="remarks">${frappe.utils.escape_html(d.remarks || "")}</textarea></p>
			`);
		}

		if (["BOSIET EBS", "FOET EBS", "HUET EBS"].includes(d.checklist_type)) {
			const $demo = $doc.find(".acl-demo-ebs");
			const demo_val = frappe.utils.escape_html(d.demo_ebs_used_by || "");
			if ($demo.length) {
				$demo.html(`<strong>Demo EBS used by:</strong> <input type="text" class="cac-cell-input cac-root-field" data-root="demo_ebs_used_by" value="${demo_val}">`);
			} else {
				$doc.find(".acl-grid").after(`<p class="acl-demo-ebs"><strong>Demo EBS used by:</strong> <input type="text" class="cac-cell-input cac-root-field" data-root="demo_ebs_used_by" value="${demo_val}"></p>`);
			}
		}
	}

	result_mark(table, idx, field, value, col_idx) {
		const mark = value || "";
		const label = mark || "·";
		const state = mark === "C" ? "is-c" : mark === "NYC" ? "is-nyc" : "is-empty";
		return `<button type="button"
			class="cac-mark-btn ${state}"
			data-table="${table}"
			data-idx="${idx}"
			data-field="${field}"
			data-col="${col_idx}"
			data-value="${frappe.utils.escape_html(mark)}"
			tabindex="0"
			title="${__("Click to cycle · → C → NYC")}"
		>${label}</button>`;
	}

	result_select(table, idx, field, value) {
		return this.result_mark(table, idx, field, value, cint(String(field).replace("result_", "")) - 1);
	}

	set_mark_btn($btn, value) {
		const mark = value || "";
		$btn.attr("data-value", mark);
		$btn.text(mark || "·");
		$btn.removeClass("is-c is-nyc is-empty");
		$btn.addClass(mark === "C" ? "is-c" : mark === "NYC" ? "is-nyc" : "is-empty");
	}

	cycle_mark($btn) {
		const current = $btn.attr("data-value") || "";
		const next = current === "" ? "C" : current === "C" ? "NYC" : "";
		this.set_mark_btn($btn, next);
	}

	bulk_set_marks(value, empty_only) {
		if (cint(this.doc?.docstatus) === 1) return;
		this.$root.find(".cac-mark-btn").each((_, el) => {
			const $btn = $(el);
			if (empty_only && ($btn.attr("data-value") || "")) return;
			this.set_mark_btn($btn, value);
		});
		frappe.show_alert({
			message: value ? __("Filled empty cells with {0}", [value]) : __("Cleared all marks"),
			indicator: "green",
		});
	}

	fill_column(col_idx, value) {
		if (cint(this.doc?.docstatus) === 1) return;
		this.$root.find(`.cac-mark-btn[data-col="${col_idx}"]`).each((_, el) => {
			this.set_mark_btn($(el), value);
		});
		frappe.show_alert({ message: __("Column filled with {0}", [value]), indicator: "green" });
	}

	bind_mark_keyboard() {
		const $root = this.$root;
		$root.off("click.cacMark keydown.cacMark");

		$root.on("click.cacMark", ".cac-mark-btn", (e) => {
			e.preventDefault();
			if (cint(this.doc?.docstatus) === 1) return;
			const $btn = $(e.currentTarget);
			this.cycle_mark($btn);
			$btn.focus();
		});

		$root.on("keydown.cacMark", ".cac-mark-btn", (e) => {
			if (cint(this.doc?.docstatus) === 1) return;
			const $btn = $(e.currentTarget);
			const key = e.key;

			if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Tab"].includes(key)) {
				e.preventDefault();
				e.stopPropagation();
				this.move_mark_focus($btn, key, e.shiftKey);
				return;
			}

			const lower = key.toLowerCase();
			if (lower === "c" || key === "1") {
				e.preventDefault();
				this.set_mark_btn($btn, "C");
				this.move_mark_focus($btn, "ArrowRight");
				return;
			}
			if (lower === "n" || key === "2") {
				e.preventDefault();
				this.set_mark_btn($btn, "NYC");
				this.move_mark_focus($btn, "ArrowRight");
				return;
			}
			if (key === " " || key === "Backspace" || key === "Delete" || key === "0") {
				e.preventDefault();
				this.set_mark_btn($btn, "");
				return;
			}
		});

		// Focus first empty/active mark for quick start
		setTimeout(() => {
			const $first =
				$root.find(".cac-mark-btn.is-empty").first().length
					? $root.find(".cac-mark-btn.is-empty").first()
					: $root.find(".cac-mark-btn").first();
			$first.trigger("focus");
		}, 50);
	}

	move_mark_focus($btn, key, shiftKey = false) {
		const row = cint($btn.data("idx"));
		const col = cint($btn.data("col"));
		let nextRow = row;
		let nextCol = col;

		if (key === "ArrowUp") nextRow -= 1;
		else if (key === "ArrowDown" || key === "Enter") nextRow += 1;
		else if (key === "ArrowLeft" || (key === "Tab" && shiftKey)) nextCol -= 1;
		else if (key === "ArrowRight" || (key === "Tab" && !shiftKey)) nextCol += 1;

		const $target = this.$root.find(
			`.cac-mark-btn[data-idx="${nextRow}"][data-col="${nextCol}"]`
		);
		if ($target.length) {
			$target.trigger("focus");
			this.scroll_mark_into_view($target);
			return;
		}

		// Wrap to next/prev row when moving horizontally off the edge
		if (key === "ArrowRight" || (key === "Tab" && !shiftKey)) {
			const $wrap = this.$root.find(`.cac-mark-btn[data-idx="${row + 1}"][data-col="0"]`);
			if ($wrap.length) {
				$wrap.trigger("focus");
				this.scroll_mark_into_view($wrap);
			}
		} else if (key === "ArrowLeft" || (key === "Tab" && shiftKey)) {
			const $prevRow = this.$root.find(`.cac-mark-btn[data-idx="${row - 1}"]`);
			if ($prevRow.length) {
				const $last = $prevRow.last();
				$last.trigger("focus");
				this.scroll_mark_into_view($last);
			}
		}
	}

	scroll_mark_into_view($btn) {
		const el = $btn.get(0);
		if (!el) return;
		el.scrollIntoView({ block: "nearest", inline: "nearest" });
	}

	text_input(table, idx, field, value) {
		return `<input type="text" class="cac-cell-input" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${frappe.utils.escape_html(value || "")}">`;
	}

	date_input_table(table, idx, field, value) {
		return `<input type="date" class="cac-date-input" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${value || ""}">`;
	}

	signature_cell(table, idx, field, value) {
		const id = `cac-sig-${table}-${idx}-${field}`.replace(/[^a-zA-Z0-9_-]/g, "_");
		const img = value ? `<img src="${value}" class="sig-img cac-sig-preview" alt="">` : "";
		return `<div class="cac-signature-wrap">
			${img}
			<canvas class="cac-signature-canvas ${value ? "has-signature" : ""}" id="${id}" width="280" height="90"></canvas>
			<input type="hidden" class="cac-signature-value" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${value || ""}">
			<div class="cac-signature-actions">
				<button type="button" class="cac-btn cac-btn-ghost cac-sig-clear" data-target="${id}">${__("Clear")}</button>
			</div>
		</div>`;
	}

	init_signature_pads() {
		this.$root.find(".cac-signature-canvas").each((_, canvas) => {
			const $wrap = $(canvas).closest(".cac-signature-wrap");
			const $hidden = $wrap.find(".cac-signature-value");
			bind_cac_signature_canvas(canvas, $hidden, $wrap);
		});

		this.$root.find(".cac-sig-clear").on("click", function (e) {
			e.preventDefault();
			const id = $(this).data("target");
			const canvas = document.getElementById(id);
			if (!canvas) return;
			const $wrap = $(canvas).closest(".cac-signature-wrap");
			const ctx = canvas.getContext("2d");
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			$wrap.find(".cac-signature-value").val("");
			$wrap.find(".cac-sig-preview").remove();
			$(canvas).removeClass("has-signature");
		});
	}

	apply_readonly_state() {
		const submitted = cint(this.doc?.docstatus) === 1;
		this.$root
			.find("input, select, textarea, canvas, button.cac-sig-clear, button.cac-mark-btn, button.cac-col-fill, button.cac-fill-c, button.cac-clear-marks")
			.prop("disabled", submitted);
		if (this.student_group_field) {
			this.student_group_field.df.read_only = submitted ? 1 : 0;
			this.student_group_field.refresh();
			this.$root.find(".cac-student-group-wrap .clearfix, .cac-student-group-wrap .control-label").remove();
		}
		if (submitted) {
			this.page.clear_primary_action();
			this.$root.find(".cac-toolbar-note").html(
				`<strong>${frappe.utils.escape_html(this.doc.checklist_type || "")}</strong> — ${__("Submitted (read-only). Use Print for the official document.")}`
			);
			this.$root.find(".cac-entry-toolbar").hide();
		} else {
			this.page.set_primary_action(__("Save"), () => this.save());
		}
	}

	collect_data() {
		const data = frappe.utils.deep_clone(this.doc) || {};
		data.student_group = this.student_group_field?.get_value() || data.student_group;

		this.$root.find(".cac-root-field").each(function () {
			const $el = $(this);
			const field = $el.data("root");
			if ($el.is(":checkbox")) {
				data[field] = $el.is(":checked") ? 1 : 0;
			} else {
				data[field] = $el.val();
			}
		});

		this.$root.find(".cac-variant-check").each(function () {
			const $el = $(this);
			data[$el.data("root")] = $el.is(":checked") ? 1 : 0;
		});

		this.$root.find(".cac-cell-input[data-table], .cac-date-input[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.val();
		});

		this.$root.find(".cac-mark-btn[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.attr("data-value") || "";
		});

		this.$root.find(".cac-signature-value[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.val();
		});

		data.learners = this.ensure_learner_rows(data.learners);
		return data;
	}

	ensure_learner_rows(learners) {
		const rows = (learners || []).slice(0, 16);
		while (rows.length < 16) {
			rows.push({ row_no: rows.length + 1, learner_name: "" });
		}
		return rows;
	}

	save() {
		if (this.saving || !this.doc || cint(this.doc.docstatus) === 1) return;

		this.saving = true;
		frappe.call({
			method: "numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.save_form",
			args: { data: this.collect_data() },
			freeze: true,
			callback: (r) => {
				this.saving = false;
				if (r.exc) return;
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				if (this.doc.name) {
					this.loading_key = null;
					frappe.set_route("course-assessor-checklist-form", this.doc.name);
				} else {
					this.fetch_form({
						checklist_type: this.doc.checklist_type,
						student_group: this.doc.student_group,
					});
				}
			},
			error: () => {
				this.saving = false;
			},
		});
	}

	submit_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the document first."));
			return;
		}
		frappe.confirm(__("Submit this Course Assessor Checklist?"), () => {
			this.save_and_then(() => {
				frappe.call({
					method: "numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.submit",
					args: { docname: this.doc.name },
					freeze: true,
					callback: (r) => {
						if (r.exc) return;
						frappe.show_alert({ message: __("Submitted"), indicator: "green" });
						this.loading_key = null;
						this.fetch_form({ docname: this.doc.name });
					},
				});
			});
		});
	}

	save_and_then(done) {
		if (cint(this.doc.docstatus) === 1) {
			done();
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.save_form",
			args: { data: this.collect_data() },
			callback: (r) => {
				if (r.exc) return;
				this.doc = r.message;
				done();
			},
		});
	}

	populate_learners() {
		const student_group = this.student_group_field?.get_value() || this.doc?.student_group;
		if (!student_group) {
			frappe.msgprint(__("Select a Student Group first."));
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.doctype.assessor_checklist.assessor_checklist.get_learners_for_student_group",
			args: { student_group },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				this.doc.learners = r.message || [];
				this.doc.student_group = student_group;
				this.loading_key = null;
				const args = this.doc.name
					? { docname: this.doc.name }
					: { checklist_type: this.doc.checklist_type, student_group };
				if (this.doc.name) {
					frappe.call({
						method: "numerouno.numerouno.page.course_assessor_checklist_form.course_assessor_checklist_form_api.save_form",
						args: { data: { ...this.collect_data(), learners: this.doc.learners, student_group } },
						callback: (save_r) => {
							if (!save_r.exc) this.doc = save_r.message;
							this.fetch_form({ docname: this.doc.name });
						},
					});
				} else {
					this.fetch_form(args);
				}
				frappe.show_alert({ message: __("Learners loaded"), indicator: "green" });
			},
		});
	}

	print_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the document before printing."));
			return;
		}
		this.save_and_then(() => frappe.set_route("print", "Assessor Checklist", this.doc.name));
	}

	open_erp_form() {
		if (this.doc?.name) frappe.set_route("Form", "Assessor Checklist", this.doc.name);
		else frappe.set_route("Form", "Assessor Checklist", "new-assessor-checklist-1");
	}
}

function bind_cac_signature_canvas(canvas, $hidden, $wrap) {
	const ctx = canvas.getContext("2d");
	let drawing = false;

	function displayHeight() {
		return parseInt(window.getComputedStyle(canvas).height, 10) || 90;
	}

	function resize() {
		const ratio = window.devicePixelRatio || 1;
		const rect = canvas.getBoundingClientRect();
		const height = displayHeight();
		canvas.width = Math.max(rect.width, 220) * ratio;
		canvas.height = height * ratio;
		ctx.setTransform(1, 0, 0, 1, 0, 0);
		ctx.scale(ratio, ratio);
		ctx.lineWidth = 2.5;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		ctx.strokeStyle = "#111";
	}

	function pointFromEvent(event) {
		const rect = canvas.getBoundingClientRect();
		const source =
			(event.touches && event.touches[0]) ||
			(event.changedTouches && event.changedTouches[0]) ||
			event;
		return { x: source.clientX - rect.left, y: source.clientY - rect.top };
	}

	function save() {
		$hidden.val(canvas.toDataURL("image/png"));
		$wrap.find(".cac-sig-preview").remove();
		$(canvas).addClass("has-signature");
	}

	function startDraw(event) {
		if (event.cancelable) event.preventDefault();
		drawing = true;
		const p = pointFromEvent(event);
		ctx.beginPath();
		ctx.moveTo(p.x, p.y);
	}

	function draw(event) {
		if (!drawing) return;
		if (event.cancelable) event.preventDefault();
		const p = pointFromEvent(event);
		ctx.lineTo(p.x, p.y);
		ctx.stroke();
		save();
	}

	function endDraw(event) {
		if (event.cancelable) event.preventDefault();
		drawing = false;
	}

	resize();
	canvas.addEventListener("mousedown", startDraw);
	canvas.addEventListener("mousemove", draw);
	canvas.addEventListener("mouseup", endDraw);
	canvas.addEventListener("mouseleave", endDraw);
	canvas.addEventListener("touchstart", startDraw, { passive: false });
	canvas.addEventListener("touchmove", draw, { passive: false });
	canvas.addEventListener("touchend", endDraw, { passive: false });
	canvas.addEventListener("touchcancel", endDraw, { passive: false });
}
