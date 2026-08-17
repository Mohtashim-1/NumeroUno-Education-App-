frappe.provide("numerouno.rospa_learning_outcome");

function lvpCint(value) {
	if (typeof cint === "function") {
		return cint(value);
	}
	const parsed = parseInt(value, 10);
	return Number.isNaN(parsed) ? 0 : parsed;
}

function lvpEscape(value) {
	if (frappe.utils && typeof frappe.utils.escape_html === "function") {
		return frappe.utils.escape_html(value || "");
	}
	return $("<div>").text(value || "").html();
}

frappe.pages["rospa-learning-outcome-form"].on_page_load = function (wrapper) {
	if (wrapper.rospa_learning_outcome_form) {
		return;
	}

	try {
		if (!$("#rospa-learning-outcome-css").length) {
			$(
				'<link id="rospa-learning-outcome-css" rel="stylesheet" type="text/css" href="/assets/numerouno/css/rospa_learning_outcome_form.css">'
			).appendTo("head");
		}

		const page =
			wrapper.page && wrapper.page.main && wrapper.page.main.length
				? wrapper.page
				: frappe.ui.make_app_page({
						parent: wrapper,
						title: __("ROSPA Learning Outcome Assessment"),
						single_column: true,
				  });

		page.main.addClass("rospa-learning-outcome-page");
		wrapper.rospa_learning_outcome_form = new numerouno.rospa_learning_outcome.Form(page);
	} catch (error) {
		$(wrapper)
			.find(".layout-main-section")
			.addBack(wrapper)
			.last()
			.html(
				`<div class="p-4">
					<h4>${__("ROSPA Learning Outcome Assessment")}</h4>
					<p class="text-danger">${__("Page failed to load. Press Ctrl+Shift+R and try again.")}</p>
				</div>`
			);
	}
};

frappe.pages["rospa-learning-outcome-form"].on_page_show = function (wrapper) {
	if (!wrapper.rospa_learning_outcome_form) {
		frappe.pages["rospa-learning-outcome-form"].on_page_load(wrapper);
		return;
	}
	wrapper.rospa_learning_outcome_form.resolve_route_and_load();
};

numerouno.rospa_learning_outcome.Form = class {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.group = null;
		this.students = [];
		this.saving = false;
		this.loading_key = null;
		this.group_field = null;
		this.$root = $('<div class="lvp-root"></div>').appendTo(this.page.main);
		this.bind_root_events();
		this.resolve_route_and_load();
	}

	bind_root_events() {
		this.$root.on("click", ".lvp-load-group", (e) => {
			e.preventDefault();
			this.load_group_students();
		});
		this.$root.on("click", ".lvp-prepare-all", (e) => {
			e.preventDefault();
			this.load_group_students(true);
		});
		this.$root.on("click", ".lvp-open-student", (e) => {
			e.preventDefault();
			const student = $(e.currentTarget).data("student");
			if (!student) {
				return;
			}
			this.fetch_form({ student_group: this.group, student });
		});
		this.$root.on("click", ".lvp-back-btn", (e) => {
			e.preventDefault();
			this.back_to_group();
		});
		this.$root.on("click", ".lvp-save-btn", (e) => {
			e.preventDefault();
			this.save();
		});
		this.$root.on("click", ".lvp-print-btn", (e) => {
			e.preventDefault();
			this.print_doc();
		});
		this.$root.on("click", ".lvp-submit-btn", (e) => {
			e.preventDefault();
			this.submit_doc();
		});
		this.$root.on("click", ".lvp-chip", (e) => {
			e.preventDefault();
			const $chip = $(e.currentTarget);
			const value = $chip.data("value");
			const idx = $chip.data("idx");
			this.set_result(idx, $chip.hasClass("is-on") ? "" : value);
		});
		this.$root.on("click", ".lvp-mark-all", (e) => {
			e.preventDefault();
			this.mark_all_pass();
		});
		this.$root.on("keydown", ".lvp-group-field-wrap input", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				this.load_group_students();
			}
		});
	}

	make_list_actions() {
		this.page.clear_inner_toolbar();
		this.page.clear_primary_action();
		this.page.set_primary_action(__("Show Learners"), () => this.load_group_students());
	}

	make_form_actions() {
		this.page.clear_inner_toolbar();
		this.page.set_secondary_action(__("Back to Learners"), () => this.back_to_group());
		this.page.set_primary_action(__("Save"), () => this.save());
	}

	back_to_group() {
		this.doc = null;
		this.loading_key = null;
		this.show_group_view(this.group);
		frappe.router.replace_route("rospa-learning-outcome-form");
	}

	resolve_route_and_load() {
		const route = frappe.get_route() || [];
		const docname = (route[1] || "").trim();
		const student_group = (frappe.route_options?.student_group || "").trim();
		const student = (frappe.route_options?.student || "").trim();

		if (frappe.route_options) {
			delete frappe.route_options.student_group;
			delete frappe.route_options.student;
		}

		if (docname && this.loading_key !== "group") {
			this.fetch_form({ docname });
			return;
		}

		if (student_group && student) {
			this.fetch_form({ student_group, student });
			return;
		}

		if (this.loading_key === "group" && this.$root.find(".lvp-group-field-wrap").length) {
			return;
		}

		this.show_group_view(student_group || this.group || null);
	}

	show_group_view(default_group = null) {
		this.doc = null;
		this.loading_key = "group";
		this.make_list_actions();
		this.page.set_title(__("ROSPA Learning Outcome Assessment"));

		this.$root.html(`
			<div class="lvp-portal-header">
				<div>
					<div class="lvp-kicker">${__("RoSPA DDLV")}</div>
					<h3>${__("Practical Assessment")}</h3>
					<p>${__("Select a student group, then open each learner to complete the ADNOC driving assessment.")}</p>
				</div>
			</div>
			<div class="lvp-card lvp-picker-card">
				<div class="lvp-group-picker">
					<div class="lvp-group-field-wrap"></div>
					<button type="button" class="lvp-btn lvp-btn-primary lvp-load-group">${__("Show Learners")}</button>
				</div>
			</div>
			<div class="lvp-summary" id="lvp-summary"></div>
			<div class="lvp-student-grid" id="lvp-student-grid">
				<div class="lvp-empty">
					<strong>${__("No class loaded yet")}</strong>
					<span>${__("Pick a student group and click Show Learners.")}</span>
				</div>
			</div>
		`);

		this.group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Student Group",
				fieldname: "student_group",
				label: __("Student Group"),
				placeholder: __("Select Student Group"),
				reqd: 1,
			},
			parent: this.$root.find(".lvp-group-field-wrap"),
			render_input: true,
		});
		this.group_field.make();
		this.group_field.refresh();
		this.$root.find(".lvp-group-field-wrap .help-box").hide();
		this.group_field.$input.attr("placeholder", __("Select Student Group"));

		const group = default_group || this.group;
		if (group) {
			this.group_field.set_value(group);
			this.load_group_students();
		}
	}

	get_student_group() {
		const from_control = this.group_field?.get_value() || "";
		const from_input = this.group_field?.$input?.val() || "";
		const from_dom = this.$root.find(".lvp-group-field-wrap input").val() || "";
		return String(from_control || from_input || from_dom || "").trim();
	}

	load_group_students(prepare = false) {
		const student_group = this.get_student_group();
		if (!student_group) {
			frappe.msgprint(__("Please select a Student Group"));
			return;
		}

		const proceed = () => {
			frappe.call({
				method:
					"numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form_api.get_students",
				args: { student_group },
				freeze: true,
				freeze_message: __("Loading learners..."),
				callback: (r) => {
					if (r.exc) {
						frappe.msgprint(__("Could not load learners for this group."));
						return;
					}
					this.group = student_group;
					this.render_student_grid(r.message || {});
				},
				error: () => {
					frappe.msgprint(__("Failed to load learners. Please try again."));
				},
			});
		};

		if (!prepare) {
			proceed();
			return;
		}

		frappe.call({
			method: "numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form_api.prepare",
			args: { student_group },
			freeze: true,
			freeze_message: __("Preparing forms..."),
			callback: (r) => {
				if (r.exc) {
					return;
				}
				const msg = r.message || {};
				frappe.show_alert({
					message: __("{0} created, {1} already existed", [msg.created_count || 0, msg.skipped_count || 0]),
					indicator: "green",
				});
				proceed();
			},
		});
	}

	render_student_grid(data) {
		const records = (data && data.records) || [];
		this.students = records;
		const grid = this.$root.find("#lvp-student-grid").get(0);
		const summary = this.$root.find("#lvp-summary").get(0);

		if (!grid) {
			return;
		}

		if (!records.length) {
			if (summary) {
				summary.style.display = "none";
				summary.innerHTML = "";
			}
			grid.innerHTML = `<div class="lvp-empty"><strong>${__("No learners in this group")}</strong></div>`;
			return;
		}

		const pending = records.filter((row) => !row.form_name).length;
		const draft = records.filter((row) => row.form_name && lvpCint(row.docstatus) === 0).length;
		const submitted = records.filter((row) => lvpCint(row.docstatus) === 1).length;

		if (summary) {
			summary.style.display = "flex";
			summary.innerHTML = "";
			[
				["lvp-pill", data.student_group || ""],
				["lvp-pill", `${records.length} ${__("learners")}`],
				["lvp-pill lvp-pill-pending", `${pending} ${__("not started")}`],
				["lvp-pill lvp-pill-draft", `${draft} ${__("draft")}`],
				["lvp-pill lvp-pill-done", `${submitted} ${__("submitted")}`],
			].forEach(([cls, text]) => {
				const pill = document.createElement("span");
				pill.className = cls;
				pill.textContent = text;
				summary.appendChild(pill);
			});
			const prepare = document.createElement("button");
			prepare.type = "button";
			prepare.className = "lvp-btn lvp-prepare-all";
			prepare.textContent = __("Prepare All Forms");
			summary.appendChild(prepare);
		}

		grid.innerHTML = "";
		records.forEach((row) => {
			const card = document.createElement("div");
			card.className = "lvp-student-card";

			const top = document.createElement("div");
			top.className = "lvp-card-top";
			const info = document.createElement("div");
			const name = document.createElement("h5");
			name.textContent = row.student_name || row.student || "";
			const company = document.createElement("p");
			company.textContent = row.employing_company || __("No company");
			info.appendChild(name);
			info.appendChild(company);

			const status = document.createElement("div");
			status.innerHTML = this.student_status(row);
			top.appendChild(info);
			top.appendChild(status);

			const btn = document.createElement("button");
			btn.type = "button";
			btn.className = "lvp-btn lvp-btn-primary lvp-open-student";
			btn.textContent = row.form_name ? __("Open Form") : __("Start Form");
			btn.setAttribute("data-student", row.student || "");

			card.appendChild(top);
			card.appendChild(btn);
			grid.appendChild(card);
		});
	}

	student_status(row) {
		if (lvpCint(row.docstatus) === 1) {
			return `<span class="lvp-status lvp-status-submitted">${__("Submitted")}</span>`;
		}
		if (row.form_name) {
			return `<span class="lvp-status lvp-status-draft">${__("Draft")}</span>`;
		}
		return `<span class="lvp-status lvp-status-pending">${__("Not started")}</span>`;
	}

	fetch_form(args) {
		this.loading_key = args.docname || `open:${args.student_group}:${args.student}`;
		this.make_form_actions();

		frappe.call({
			method:
				"numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form_api.get_form_html",
			args,
			freeze: true,
			callback: (r) => {
				if (r.exc) {
					this.loading_key = null;
					return;
				}
				this.doc = r.message.doc;
				this.render();
				const title = this.doc.candidate_name || this.doc.student || __("Assessment");
				this.page.set_title(`${__("ROSPA Learning Outcome Assessment")} — ${title}`);
				if (this.doc.name) {
					frappe.router.replace_route("rospa-learning-outcome-form", this.doc.name);
				}
			},
			error: () => {
				this.loading_key = null;
			},
		});
	}

	render() {
		if (!this.doc) {
			return;
		}

		const d = this.doc;
		const rows = d.criteria || [];
		const done = rows.filter((row) => (row.result || "") === "Pass").length;

		this.$root.html(`
			<div class="lvp-form-bar">
				<button type="button" class="lvp-btn lvp-back-btn">${__("Back to Learners")}</button>
				<div class="lvp-form-bar-meta">
					<strong>${lvpEscape(d.candidate_name || "")}</strong>
					<span>${lvpEscape(d.student_group || "")}</span>
				</div>
				<button type="button" class="lvp-btn lvp-btn-primary lvp-save-btn">${__("Save")}</button>
			</div>

			<div class="lvp-entry">
				<section class="lvp-section-card">
					<h4>${__("Learner details")}</h4>
					<div class="lvp-fields">
						<label class="lvp-field">
							<span>${__("Learner Name")}</span>
							${this.text_input_root("candidate_name", d.candidate_name)}
						</label>
						<label class="lvp-field">
							<span>${__("Date")}</span>
							${this.date_input("assessment_date", d.assessment_date)}
						</label>
					</div>
				</section>

				<section class="lvp-section-card">
					<div class="lvp-section-head">
						<div>
							<h4>${d.form_title || __("Learning Outcome Assessment Record")}</h4>
							<p>${__("Mark each criterion Pass or Fail and add comments where needed.")}</p>
						</div>
						<div class="lvp-progress-wrap">
							<div class="lvp-progress"><b id="lvp-progress-count">${done}</b> / ${rows.length} ${__("pass")}</div>
							<button type="button" class="lvp-btn lvp-mark-all">${__("Mark all Pass")}</button>
						</div>
					</div>
					<div class="lvp-checklist">${this.criteria_html()}</div>
				</section>

				<section class="lvp-section-card">
					<h4>${__("Assessor")}</h4>
					<div class="lvp-fields">
						<label class="lvp-field">
							<span>${__("Assessor name")}</span>
							${this.text_input_root("assessor_name", d.assessor_name)}
						</label>
						<label class="lvp-field">
							<span>${__("Assessor date")}</span>
							${this.date_input("assessor_date", d.assessor_date)}
						</label>
					</div>
					<div class="lvp-footer-actions">
						<button type="button" class="lvp-btn lvp-print-btn">${__("Print")}</button>
						<button type="button" class="lvp-btn lvp-submit-btn">${__("Submit")}</button>
						<button type="button" class="lvp-btn lvp-btn-primary lvp-save-btn">${__("Save")}</button>
					</div>
				</section>
			</div>
		`);

		this.apply_readonly_state();
	}

	criteria_html() {
		const rows = this.doc.criteria || [];
		let last_outcome = "";
		return rows
			.map((row, idx) => {
				const outcome = row.outcome || "";
				let heading = "";
				if (outcome && outcome !== last_outcome) {
					last_outcome = outcome;
					heading = `<div class="lvp-group-title">${lvpEscape(outcome)}</div>`;
				}
				const text = (row.criterion || "").trim();
				const result = row.result || "";
				const body = `<p class="lvp-item-text"><b>${lvpEscape(row.criterion_no || "")}</b> ${lvpEscape(text).replace(/\n/g, "<br>")}</p>`;
				return `${heading}
					<div class="lvp-item ${result === "Pass" ? "is-achieved" : result === "Fail" ? "is-fail" : ""}" data-idx="${idx}">
						<div class="lvp-item-num">${lvpEscape(row.criterion_no || String(idx + 1))}</div>
						<div class="lvp-item-body">
							${body}
							<div class="lvp-item-actions">
								<button type="button" class="lvp-chip ${result === "Pass" ? "is-on" : ""}" data-idx="${idx}" data-value="Pass">${__("Pass")}</button>
								<button type="button" class="lvp-chip lvp-chip-fail ${result === "Fail" ? "is-on" : ""}" data-idx="${idx}" data-value="Fail">${__("Fail")}</button>
							</div>
							<textarea class="lvp-item-input" data-field="comments" data-idx="${idx}" placeholder="${__("Comments")}">${lvpEscape(row.comments || "")}</textarea>
						</div>
					</div>`;
			})
			.join("");
	}

	set_result(idx, value) {
		const $item = this.$root.find(`.lvp-item[data-idx="${idx}"]`);
		$item.find(".lvp-chip").each((_, el) => {
			$(el).toggleClass("is-on", $(el).data("value") === value);
		});
		$item.toggleClass("is-achieved", value === "Pass");
		$item.toggleClass("is-fail", value === "Fail");
		this.update_progress();
	}

	mark_all_pass() {
		this.$root.find(".lvp-item").each((_, el) => {
			this.set_result($(el).data("idx"), "Pass");
		});
	}

	update_progress() {
		this.$root.find("#lvp-progress-count").text(this.$root.find('.lvp-chip.is-on[data-value="Pass"]').length);
	}

	text_input_root(field, value) {
		return `<input type="text" class="lvp-cell-input" data-root="${field}" value="${lvpEscape(value || "")}">`;
	}

	text_area_root(field, value) {
		return `<textarea class="lvp-cell-input" rows="3" data-root="${field}">${lvpEscape(value || "")}</textarea>`;
	}

	date_input(field, value) {
		return `<input type="date" class="lvp-cell-input" data-root="${field}" value="${value || ""}">`;
	}

	collect_payload() {
		const payload = frappe.utils.deep_clone(this.doc || {});
		this.$root.find("[data-root]").each((_, el) => {
			payload[$(el).data("root")] = $(el).val();
		});
		(payload.criteria || []).forEach((row, idx) => {
			const $item = this.$root.find(`.lvp-item[data-idx="${idx}"]`);
			row.result = $item.find(".lvp-chip.is-on").data("value") || "";
			row.comments = $item.find("[data-field='comments']").val() || "";
		});
		return payload;
	}

	apply_readonly_state() {
		const readonly = lvpCint(this.doc?.docstatus) === 1;
		this.$root.find("input, select, textarea, .lvp-toggle, .lvp-chip, .lvp-mark-all").prop("disabled", readonly);
		if (readonly) {
			this.page.clear_primary_action();
			this.$root.find(".lvp-save-btn, .lvp-submit-btn, .lvp-mark-all").hide();
		}
	}

	save() {
		if (this.saving || lvpCint(this.doc?.docstatus) === 1) {
			return;
		}
		this.saving = true;

		frappe.call({
			method: "numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form_api.save_form",
			args: { data: this.collect_payload() },
			freeze: true,
			freeze_message: __("Saving..."),
			callback: (r) => {
				this.saving = false;
				if (r.exc) {
					return;
				}
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				if (this.doc.name) {
					frappe.router.replace_route("rospa-learning-outcome-form", this.doc.name);
				}
			},
			error: () => {
				this.saving = false;
			},
		});
	}

	submit_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Save the form first."));
			return;
		}
		frappe.confirm(__("Submit this assessment?"), () => {
			frappe.call({
				method: "numerouno.numerouno.page.rospa_learning_outcome_form.rospa_learning_outcome_form_api.submit",
				args: { docname: this.doc.name },
				callback: (r) => {
					if (r.exc) {
						return;
					}
					this.doc.docstatus = r.message.docstatus;
					this.apply_readonly_state();
					frappe.show_alert({ message: __("Submitted"), indicator: "green" });
				},
			});
		});
	}

	print_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Save the form first."));
			return;
		}
		localStorage.setItem(
			"print_format:ROSPA Learning Outcome Assessment",
			"ROSPA Learning Outcome Assessment Form"
		);
		frappe.route_options = {
			format: "ROSPA Learning Outcome Assessment Form",
			no_letterhead: 1,
		};
		frappe.set_route("print", "ROSPA Learning Outcome Assessment", this.doc.name);
	}
};
