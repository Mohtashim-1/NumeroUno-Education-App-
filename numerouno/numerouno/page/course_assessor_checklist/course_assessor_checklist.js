frappe.pages["course-assessor-checklist"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Course Assessor Checklist"),
		single_column: true,
	});

	page.main.addClass("course-assessor-checklist-page");
	wrapper.course_assessor_checklist = new CourseAssessorChecklist(page);
};

frappe.pages["course-assessor-checklist"].on_page_show = function (wrapper) {
	wrapper.course_assessor_checklist?.resolve_route_and_load();
};

class CourseAssessorChecklist {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.saving = false;
		this.loading_key = null;

		this.$root = $('<div class="cac-root"></div>').appendTo(this.page.main);
		this.make_actions();
		this.resolve_route_and_load();
	}

	make_actions() {
		this.page.set_primary_action(__("Save"), () => this.save());
		this.page.add_inner_button(__("Print"), () => this.print_doc(), __("Actions"));
		this.page.add_inner_button(__("Submit"), () => this.submit_doc(), __("Actions"));
		this.page.add_inner_button(__("Populate Learners"), () => this.populate_learners(), __("Actions"));
		this.page.add_inner_button(__("ERP Form"), () => this.open_erp_form(), __("Actions"));
		this.page.add_inner_button(__("New"), () => this.show_picker(), __("Actions"));
	}

	resolve_route_and_load() {
		const route = frappe.get_route() || [];
		const docname = (route[1] || frappe.route_options?.name || frappe.utils.get_query_params().name || "").trim();
		const checklist_type = (frappe.route_options?.checklist_type || frappe.utils.get_query_params().checklist_type || "").trim();
		const student_group = frappe.route_options?.student_group || frappe.utils.get_query_params().student_group || null;

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

		this.show_picker();
	}

	show_picker() {
		this.doc = null;
		this.loading_key = "picker";
		const types = [
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

		const options = types
			.map((t) => `<option value="${frappe.utils.escape_html(t)}">${frappe.utils.escape_html(t)}</option>`)
			.join("");

		this.$root.html(`
			<div class="cac-picker">
				<h4>${__("Create Course Assessor Checklist")}</h4>
				<p class="text-muted">${__("Select the checklist type matching your Word form (NUTC-P14-F01 series).")}</p>
				<div class="form-group">
					<label class="control-label">${__("Checklist Type")}</label>
					<select class="form-control cac-new-type">${options}</select>
				</div>
				<div class="form-group cac-group-field-wrap">
					<label class="control-label">${__("Student Group")} (${__("optional")})</label>
				</div>
				<div class="cac-picker-actions">
					<button class="btn btn-primary btn-sm cac-open-new">${__("Open Form")}</button>
				</div>
			</div>
		`);

		const group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Student Group",
				fieldname: "student_group",
				label: __("Student Group"),
			},
			parent: this.$root.find(".cac-group-field-wrap"),
			render_input: true,
		});
		group_field.make();
		group_field.refresh();
		this.picker_group_field = group_field;

		this.$root.find(".cac-open-new").on("click", () => {
			const checklist_type = this.$root.find(".cac-new-type").val();
			const student_group = this.picker_group_field.get_value();
			if (!checklist_type) {
				frappe.msgprint(__("Select a Checklist Type"));
				return;
			}
			this.loading_key = null;
			this.fetch_form({ checklist_type, student_group: student_group || null });
		});
	}

	fetch_form(args) {
		const load_key = args.docname || `new:${args.checklist_type || ""}:${args.student_group || ""}`;
		this.loading_key = load_key;

		frappe.call({
			method: "numerouno.numerouno.page.course_assessor_checklist.course_assessor_checklist_api.get_form_html",
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
			<p class="cac-toolbar-note">
				<strong>${frappe.utils.escape_html(this.doc.checklist_type || "")}</strong>
				${this.doc.form_code ? ` — ${frappe.utils.escape_html(this.doc.form_code)}` : ""}
				<br>${__("Layout matches the official assessor checklist. Click Save to store changes.")}
			</p>
			<div class="cac-header-fields">
				<div class="form-group">
					<label class="control-label">${__("Assessment Date")}</label>
					<input type="date" class="cac-date-input cac-root-field" data-root="assessment_date" value="${this.doc.assessment_date || ""}">
				</div>
				<div class="form-group cac-student-group-wrap">
					<label class="control-label">${__("Student Group")}</label>
				</div>
			</div>
			<div class="cac-doc-wrap">
				<div class="cac-doc">${html}</div>
			</div>
		`);

		const group_field = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Student Group",
				fieldname: "student_group",
				label: __("Student Group"),
				change: () => {
					this.doc.student_group = group_field.get_value();
				},
			},
			parent: this.$root.find(".cac-student-group-wrap"),
			render_input: true,
		});
		group_field.make();
		group_field.set_value(this.doc.student_group || "");
		group_field.refresh();
		this.student_group_field = group_field;

		this.enhance_editable();
		this.init_signature_pads();
		this.apply_readonly_state();
	}

	enhance_editable() {
		const d = this.doc;
		const $doc = this.$root.find(".cac-doc");
		const outcome_count = (d.outcomes || []).length;

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

		$doc.find(".acl-grid tr").each((row_idx, tr) => {
			if ($(tr).hasClass("acl-grid-head")) return;
			const learner_idx = cint($(tr).find(".col-no").text().trim()) - 1;
			if (learner_idx < 0 || learner_idx > 15) return;
			const row = (d.learners || [])[learner_idx] || {};

			$(tr).find(".col-name").html(
				this.text_input("learners", learner_idx, "learner_name", row.learner_name)
			);

			$(tr).find(".col-result").each((col_idx, cell) => {
				const field = `result_${col_idx + 1}`;
				if (col_idx + 1 > outcome_count) return;
				$(cell).html(this.result_select("learners", learner_idx, field, row[field]));
			});
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

	text_input(table, idx, field, value) {
		return `<input type="text" class="cac-cell-input" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${frappe.utils.escape_html(value || "")}">`;
	}

	result_select(table, idx, field, value) {
		const options = ["", "C", "NYC"]
			.map((opt) => {
				const selected = (value || "") === opt ? " selected" : "";
				return `<option value="${opt}"${selected}>${opt || "-"}</option>`;
			})
			.join("");
		return `<select class="cac-result-select" data-table="${table}" data-idx="${idx}" data-field="${field}">${options}</select>`;
	}

	date_input_table(table, idx, field, value) {
		return `<input type="date" class="cac-date-input" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${value || ""}">`;
	}

	signature_cell(table, idx, field, value) {
		const id = `cac-sig-${table}-${idx}-${field}`.replace(/[^a-zA-Z0-9_-]/g, "_");
		const img = value ? `<img src="${value}" class="sig-img cac-sig-preview" alt="">` : "";
		return `<div class="cac-signature-wrap">
			${img}
			<canvas class="cac-signature-canvas ${value ? "has-signature" : ""}" id="${id}" width="120" height="28"></canvas>
			<input type="hidden" class="cac-signature-value" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${value || ""}">
			<div class="cac-signature-actions"><button type="button" class="cac-sig-clear" data-target="${id}">${__("Clear")}</button></div>
		</div>`;
	}

	init_signature_pads() {
		this.$root.find(".cac-signature-canvas").each(function () {
			const canvas = this;
			const $wrap = $(canvas).closest(".cac-signature-wrap");
			const $hidden = $wrap.find(".cac-signature-value");
			const ctx = canvas.getContext("2d");
			let drawing = false;

			function pointFromEvent(event) {
				const rect = canvas.getBoundingClientRect();
				const source = event.touches ? event.touches[0] : event;
				return { x: source.clientX - rect.left, y: source.clientY - rect.top };
			}

			function save() {
				$hidden.val(canvas.toDataURL("image/png"));
				$wrap.find(".cac-sig-preview").remove();
				$(canvas).addClass("has-signature");
			}

			ctx.lineWidth = 1.5;
			ctx.lineCap = "round";
			ctx.strokeStyle = "#000";

			canvas.addEventListener("mousedown", (e) => {
				drawing = true;
				const p = pointFromEvent(e);
				ctx.beginPath();
				ctx.moveTo(p.x, p.y);
			});
			canvas.addEventListener("mousemove", (e) => {
				if (!drawing) return;
				const p = pointFromEvent(e);
				ctx.lineTo(p.x, p.y);
				ctx.stroke();
				save();
			});
			canvas.addEventListener("mouseup", () => {
				drawing = false;
			});
			canvas.addEventListener("mouseleave", () => {
				drawing = false;
			});
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
		this.$root.find("input, select, textarea, canvas, button.cac-sig-clear").prop("disabled", submitted);
		if (this.student_group_field) {
			this.student_group_field.df.read_only = submitted ? 1 : 0;
			this.student_group_field.refresh();
		}
		if (submitted) {
			this.page.clear_primary_action();
			this.$root.find(".cac-toolbar-note").html(
				`<strong>${frappe.utils.escape_html(this.doc.checklist_type || "")}</strong> — ${__("Submitted (read-only). Use Print for the official document.")}`
			);
		} else if (!this.page.btn_primary?.length) {
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

		this.$root.find(".cac-cell-input[data-table], .cac-result-select[data-table], .cac-date-input[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.val();
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
			method: "numerouno.numerouno.page.course_assessor_checklist.course_assessor_checklist_api.save_form",
			args: { data: this.collect_data() },
			freeze: true,
			callback: (r) => {
				this.saving = false;
				if (r.exc) return;
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				if (this.doc.name) {
					this.loading_key = null;
					frappe.set_route("course-assessor-checklist", this.doc.name);
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
					method: "numerouno.numerouno.page.course_assessor_checklist.course_assessor_checklist_api.submit",
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
			method: "numerouno.numerouno.page.course_assessor_checklist.course_assessor_checklist_api.save_form",
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
						method: "numerouno.numerouno.page.course_assessor_checklist.course_assessor_checklist_api.save_form",
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
