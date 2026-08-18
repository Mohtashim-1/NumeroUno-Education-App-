frappe.provide("numerouno.rospa_practical");

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

frappe.pages["rospa-practical-assessment-form"].on_page_load = function (wrapper) {
	if (wrapper.rospa_practical_assessment_form) {
		return;
	}

	try {
		if (!$("#rospa-practical-assessment-css").length) {
			$(
				'<link id="rospa-practical-assessment-css" rel="stylesheet" type="text/css" href="/assets/numerouno/css/rospa_practical_assessment_form.css">'
			).appendTo("head");
		}

		const page =
			wrapper.page && wrapper.page.main && wrapper.page.main.length
				? wrapper.page
				: frappe.ui.make_app_page({
						parent: wrapper,
						title: __("ROSPA Practical Assessment"),
						single_column: true,
				  });

		page.main.addClass("rospa-practical-assessment-page");
		wrapper.rospa_practical_assessment_form = new numerouno.rospa_practical.Form(page);
	} catch (error) {
		$(wrapper)
			.find(".layout-main-section")
			.addBack(wrapper)
			.last()
			.html(
				`<div class="p-4">
					<h4>${__("ROSPA Practical Assessment")}</h4>
					<p class="text-danger">${__("Page failed to load. Press Ctrl+Shift+R and try again.")}</p>
				</div>`
			);
	}
};

frappe.pages["rospa-practical-assessment-form"].on_page_show = function (wrapper) {
	if (!wrapper.rospa_practical_assessment_form) {
		frappe.pages["rospa-practical-assessment-form"].on_page_load(wrapper);
		return;
	}
	wrapper.rospa_practical_assessment_form.resolve_route_and_load();
};

numerouno.rospa_practical.Form = class {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.group = null;
		this.students = [];
		this.saving = false;
		this.loading_key = null;
		this.group_field = null;
		this.assessor_field = null;
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
		this.$root.on("click", ".lvp-toggle", (e) => {
			e.preventDefault();
			this.toggle_achieved($(e.currentTarget).data("idx"));
		});
		this.$root.on("click", ".lvp-chip", (e) => {
			e.preventDefault();
			const $chip = $(e.currentTarget);
			this.set_source($chip.data("idx"), $chip.hasClass("is-on") ? "" : $chip.data("value"));
		});
		this.$root.on("click", ".lvp-mark-all", (e) => {
			e.preventDefault();
			this.mark_all_achieved();
		});
		this.$root.on("click", ".lvp-form-sign-clear", (e) => {
			e.preventDefault();
			this.clear_form_signature();
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
		frappe.router.replace_route("rospa-practical-assessment-form");
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
		this.page.set_title(__("ROSPA Practical Assessment"));

		this.$root.html(`
			<div class="lvp-portal-header">
				<div>
					<div class="lvp-kicker">${__("ROSPA")}</div>
					<h3>${__("Practical Assessment")}</h3>
					<p>${__("Select a student group, then open each learner to complete the RoSPA practical assessment.")}</p>
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
					"numerouno.numerouno.page.rospa_practical_assessment_form.rospa_practical_assessment_form_api.get_students",
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
			method: "numerouno.numerouno.page.rospa_practical_assessment_form.rospa_practical_assessment_form_api.prepare",
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
				"numerouno.numerouno.page.rospa_practical_assessment_form.rospa_practical_assessment_form_api.get_form_html",
			args,
			freeze: true,
			callback: (r) => {
				if (r.exc) {
					this.loading_key = null;
					return;
				}
				this.doc = r.message.doc;
				this.render();
				this.init_signature_canvases();
				const title = this.doc.candidate_name || this.doc.student || __("Assessment");
				this.page.set_title(`${__("ROSPA Practical Assessment")} — ${title}`);
				if (this.doc.name) {
					frappe.router.replace_route("rospa-practical-assessment-form", this.doc.name);
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
		const done = rows.filter((row) => lvpCint(row.achieved)).length;

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
					<h4>${__("Candidate details")}</h4>
					<div class="lvp-fields">
						<label class="lvp-field">
							<span>${__("Candidate Name")}</span>
							${this.text_input_root("candidate_name", d.candidate_name)}
						</label>
						<label class="lvp-field">
							<span>${__("Date")}</span>
							${this.date_input("assessment_date", d.assessment_date)}
						</label>
						<label class="lvp-field">
							<span>${__("Employing Company")}</span>
							${this.text_input_root("employing_company", d.employing_company)}
						</label>
						<label class="lvp-field">
							<span>${__("Mobile Number")}</span>
							${this.text_input_root("mobile_number", d.mobile_number)}
						</label>
						<label class="lvp-field lvp-field-full">
							<span>${__("Student Signature")}</span>
							${this.learner_signature_html(d)}
						</label>
					</div>
				</section>

				<section class="lvp-section-card">
					<div class="lvp-section-head">
						<div>
							<h4>${d.form_title || __("Practical Assessment")}</h4>
							<p>${__("Tap Achieved, then choose how you saw it: O Observation, S Simulation, Q Questioning, W Witness.")}</p>
						</div>
						<div class="lvp-progress-wrap">
							<div class="lvp-progress"><b id="lvp-progress-count">${done}</b> / ${rows.length} ${__("achieved")}</div>
							<button type="button" class="lvp-btn lvp-mark-all">${__("Mark all achieved")}</button>
						</div>
					</div>
					<div class="lvp-checklist">${this.criteria_html()}</div>
				</section>

				<section class="lvp-section-card">
					<h4>${__("Assessor notes")}</h4>
					<div class="lvp-fields lvp-fields-stack">
						<label class="lvp-field lvp-field-full">
							<span>${__("Remarks")}</span>
							${this.text_area_root("remarks", d.remarks)}
						</label>
						<label class="lvp-field lvp-field-full">
							<span>${__("Training and development needs")}</span>
							${this.text_area_root("training_development_needs", d.training_development_needs)}
						</label>
						<label class="lvp-field">
							<span>${__("Assessor")}</span>
							<div class="lvp-assessor-wrap"></div>
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

		this.make_assessor_field(d);
		this.apply_readonly_state();
	}

	make_assessor_field(doc) {
		this.assessor_field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Instructor",
				fieldname: "assessor",
				label: __("Assessor"),
				placeholder: __("Select Instructor"),
			},
			parent: this.$root.find(".lvp-assessor-wrap"),
			render_input: true,
		});
		this.assessor_field.make();
		this.assessor_field.refresh();
		this.$root.find(".lvp-assessor-wrap .help-box, .lvp-assessor-wrap .control-label").hide();
		this.assessor_field.$input.attr("placeholder", __("Select Instructor"));
		if (doc.assessor) {
			this.assessor_field.set_value(doc.assessor);
		}
	}

	criteria_html() {
		const rows = this.doc.criteria || [];
		let last_section = "";
		return rows
			.map((row, idx) => {
				const section = row.section || "";
				let heading = "";
				if (section && section !== last_section) {
					last_section = section;
					heading = `<div class="lvp-group-title">${lvpEscape(section)}</div>`;
				}
				const text = (row.criterion || "").trim();
				const achieved = lvpCint(row.achieved);
				const source = row.source_of_evidence || "";
				const body = text
					? `<p class="lvp-item-text">${lvpEscape(text)}</p>`
					: `<input type="text" class="lvp-item-input" data-table="criteria" data-idx="${idx}" data-field="criterion" placeholder="${__(
							"Type the criterion here"
					  )}" value="${lvpEscape(row.criterion || "")}">`;
				const chips = ["O", "S", "Q", "W"]
					.map(
						(value) =>
							`<button type="button" class="lvp-chip ${source === value ? "is-on" : ""}" data-idx="${idx}" data-value="${value}">${value}</button>`
					)
					.join("");
				return `${heading}
					<div class="lvp-item ${achieved ? "is-achieved" : ""}" data-idx="${idx}">
						<div class="lvp-item-num">${row.sr_no || idx + 1}</div>
						<div class="lvp-item-body">
							${body}
							<div class="lvp-item-actions">
								<button type="button" class="lvp-toggle ${achieved ? "is-on" : ""}" data-idx="${idx}">${__("Achieved")}</button>
								<div class="lvp-chips">${chips}</div>
							</div>
						</div>
					</div>`;
			})
			.join("");
	}

	toggle_achieved(idx) {
		const $item = this.$root.find(`.lvp-item[data-idx="${idx}"]`);
		const $toggle = $item.find(".lvp-toggle");
		const on = !$toggle.hasClass("is-on");
		$toggle.toggleClass("is-on", on);
		$item.toggleClass("is-achieved", on);
		if (on && !$item.find(".lvp-chip.is-on").length) {
			this.set_source(idx, "O");
		}
		this.update_progress();
	}

	set_source(idx, value) {
		const $item = this.$root.find(`.lvp-item[data-idx="${idx}"]`);
		$item.find(".lvp-chip").each((_, el) => {
			$(el).toggleClass("is-on", $(el).data("value") === value);
		});
		if (value) {
			$item.addClass("is-achieved");
			$item.find(".lvp-toggle").addClass("is-on");
		}
		this.update_progress();
	}

	mark_all_achieved() {
		this.$root.find(".lvp-item").each((_, el) => {
			const idx = $(el).data("idx");
			$(el).addClass("is-achieved");
			$(el).find(".lvp-toggle").addClass("is-on");
			if (!$(el).find(".lvp-chip.is-on").length) {
				this.set_source(idx, "O");
			}
		});
		this.update_progress();
	}

	update_progress() {
		this.$root.find("#lvp-progress-count").text(this.$root.find(".lvp-toggle.is-on").length);
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

	learner_signature_html(doc) {
		const value = doc.learner_signature || "";
		const img = value ? `<img src="${lvpEscape(value)}" class="lvp-sign-img" alt="Signature">` : "";
		return `<div class="lvp-sign-wrap">
			${img}
			<canvas class="lvp-sign-canvas lvp-form-sign-canvas ${value ? "has-signature" : ""}" width="280" height="90"></canvas>
			<input type="hidden" class="lvp-learner-sig-value" data-root="learner_signature" value="${lvpEscape(value)}">
			<div class="lvp-sign-actions">
				<button type="button" class="lvp-btn lvp-form-sign-clear">${__("Clear")}</button>
			</div>
		</div>`;
	}

	init_signature_canvases() {
		this.$root.find(".lvp-sign-canvas").each((_, canvas) => {
			this.bind_signature_canvas(canvas);
		});
	}

	bind_signature_canvas(canvas) {
		if (!canvas || canvas.dataset.bound === "1") {
			return;
		}
		canvas.dataset.bound = "1";
		const ctx = canvas.getContext("2d");
		ctx.strokeStyle = "#122033";
		ctx.lineWidth = 2;
		ctx.lineCap = "round";
		let drawing = false;

		const coords = (e) => {
			const rect = canvas.getBoundingClientRect();
			const src = e.touches && e.touches[0] ? e.touches[0] : e;
			return {
				x: (src.clientX - rect.left) * (canvas.width / rect.width),
				y: (src.clientY - rect.top) * (canvas.height / rect.height),
			};
		};
		const start = (e) => {
			e.preventDefault();
			drawing = true;
			const p = coords(e);
			ctx.beginPath();
			ctx.moveTo(p.x, p.y);
			canvas.dataset.dirty = "1";
		};
		const move = (e) => {
			if (!drawing) {
				return;
			}
			e.preventDefault();
			const p = coords(e);
			ctx.lineTo(p.x, p.y);
			ctx.stroke();
		};
		const end = (e) => {
			if (e) {
				e.preventDefault();
			}
			drawing = false;
			const $hidden = $(canvas).closest(".lvp-sign-wrap").find(".lvp-learner-sig-value");
			if ($hidden.length && this.canvas_has_ink(canvas)) {
				$hidden.val(canvas.toDataURL("image/png"));
			}
		};

		canvas.addEventListener("mousedown", start);
		canvas.addEventListener("mousemove", move);
		canvas.addEventListener("mouseup", end);
		canvas.addEventListener("mouseleave", () => {
			drawing = false;
		});
		canvas.addEventListener("touchstart", start, { passive: false });
		canvas.addEventListener("touchmove", move, { passive: false });
		canvas.addEventListener("touchend", end, { passive: false });
	}

	canvas_has_ink(canvas) {
		const ctx = canvas.getContext("2d");
		const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
		for (let i = 3; i < pixels.length; i += 4) {
			if (pixels[i] !== 0) {
				return true;
			}
		}
		return false;
	}

	clear_form_signature() {
		const canvas = this.$root.find(".lvp-form-sign-canvas").get(0);
		if (canvas) {
			canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
			canvas.dataset.dirty = "";
			$(canvas).removeClass("has-signature");
		}
		this.$root.find(".lvp-learner-sig-value").val("");
		this.$root.find(".lvp-sign-wrap .lvp-sign-img").remove();
	}

	collect_payload() {
		const payload = frappe.utils.deep_clone(this.doc || {});
		this.$root.find("[data-root]").each((_, el) => {
			payload[$(el).data("root")] = $(el).val();
		});
		payload.assessor = this.assessor_field?.get_value() || this.assessor_field?.$input?.val() || "";
		const formCanvas = this.$root.find(".lvp-form-sign-canvas").get(0);
		if (formCanvas && this.canvas_has_ink(formCanvas)) {
			payload.learner_signature = formCanvas.toDataURL("image/png");
		}
		(payload.criteria || []).forEach((row, idx) => {
			const $item = this.$root.find(`.lvp-item[data-idx="${idx}"]`);
			row.achieved = $item.find(".lvp-toggle.is-on").length ? 1 : 0;
			row.source_of_evidence = $item.find(".lvp-chip.is-on").data("value") || "";
			const $criterion = $item.find("[data-field='criterion']");
			if ($criterion.length) {
				row.criterion = $criterion.val();
			}
		});
		return payload;
	}

	apply_readonly_state() {
		const readonly = lvpCint(this.doc?.docstatus) === 1;
		this.$root.find("input, select, textarea, .lvp-toggle, .lvp-chip, .lvp-mark-all, .lvp-form-sign-clear").prop("disabled", readonly);
		if (this.assessor_field) {
			this.assessor_field.df.read_only = readonly ? 1 : 0;
			this.assessor_field.refresh();
			this.$root.find(".lvp-assessor-wrap .help-box, .lvp-assessor-wrap .control-label").hide();
		}
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
			method: "numerouno.numerouno.page.rospa_practical_assessment_form.rospa_practical_assessment_form_api.save_form",
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
					frappe.router.replace_route("rospa-practical-assessment-form", this.doc.name);
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
				method: "numerouno.numerouno.page.rospa_practical_assessment_form.rospa_practical_assessment_form_api.submit",
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
			"print_format:ROSPA Practical Assessment",
			"ROSPA Practical Assessment Form"
		);
		frappe.route_options = {
			format: "ROSPA Practical Assessment Form",
			no_letterhead: 1,
		};
		frappe.set_route("print", "ROSPA Practical Assessment", this.doc.name);
	}
};
