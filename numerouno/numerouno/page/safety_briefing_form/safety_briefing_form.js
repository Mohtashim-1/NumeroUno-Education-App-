frappe.pages["safety-briefing-form"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Safety Briefing Form"),
		single_column: true,
	});

	page.main.addClass("safety-briefing-form-page");
	wrapper.safety_briefing_form = new SafetyBriefingForm(page);
};

frappe.pages["safety-briefing-form"].on_page_show = function (wrapper) {
	wrapper.safety_briefing_form?.resolve_route_and_load();
};

class SafetyBriefingForm {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.saving = false;
		this.loading_key = null;

		this.$root = $('<div class="sbf-root"></div>').appendTo(this.page.main);
		this.make_actions();
		this.resolve_route_and_load();
	}

	make_actions() {
		this.page.set_primary_action(__("Save"), () => this.save());
		this.page.add_inner_button(__("Print"), () => this.print_doc(), __("Actions"));
		this.page.add_inner_button(__("Submit"), () => this.submit_doc(), __("Actions"));
		this.page.add_inner_button(__("Populate Attendees"), () => this.populate_attendees(), __("Actions"));
		this.page.add_inner_button(__("ERP Form"), () => this.open_erp_form(), __("Actions"));
		this.page.add_inner_button(__("New"), () => this.show_picker(), __("Actions"));
	}

	resolve_route_and_load() {
		const route = frappe.get_route() || [];
		const docname = (route[1] || frappe.route_options?.name || frappe.utils.get_query_params().name || "").trim();
		const briefing_type = (frappe.route_options?.briefing_type || frappe.utils.get_query_params().briefing_type || "").trim();
		const student_group = frappe.route_options?.student_group || frappe.utils.get_query_params().student_group || null;

		const load_key = docname || `new:${briefing_type}:${student_group || ""}`;
		if (this.loading_key === load_key && this.doc && (docname ? this.doc.name === docname : !this.doc.name)) {
			return;
		}
		this.loading_key = load_key;

		if (docname) {
			this.fetch_form({ docname });
			return;
		}

		if (briefing_type) {
			this.fetch_form({ briefing_type, student_group });
			return;
		}

		this.show_picker();
	}

	show_picker() {
		this.doc = null;
		this.loading_key = "picker";
		const types = [
			"Basic H2S",
			"TBOSIET",
			"TSbB",
			"TFOET",
			"THUET",
			"BOSIET EBS",
			"FOET EBS",
			"HUET EBS",
		];

		const options = types
			.map((t) => `<option value="${frappe.utils.escape_html(t)}">${frappe.utils.escape_html(t)}</option>`)
			.join("");

		this.$root.html(`
			<div class="sbf-picker">
				<h4>${__("Create Safety Briefing")}</h4>
				<p class="text-muted">${__("Select the briefing type matching your Word form (NUTC-P11-F02 series).")}</p>
				<div class="form-group">
					<label class="control-label">${__("Briefing Type")}</label>
					<select class="form-control sbf-new-type">${options}</select>
				</div>
				<div class="form-group sbf-group-field-wrap">
					<label class="control-label">${__("Student Group")} (${__("optional")})</label>
				</div>
				<div class="sbf-picker-actions">
					<button class="btn btn-primary btn-sm sbf-open-new">${__("Open Form")}</button>
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
			parent: this.$root.find(".sbf-group-field-wrap"),
			render_input: true,
		});
		group_field.make();
		group_field.refresh();
		this.picker_group_field = group_field;

		this.$root.find(".sbf-open-new").on("click", () => {
			const briefing_type = this.$root.find(".sbf-new-type").val();
			const student_group = this.picker_group_field.get_value();
			if (!briefing_type) {
				frappe.msgprint(__("Select a Briefing Type"));
				return;
			}
			this.loading_key = null;
			this.fetch_form({ briefing_type, student_group: student_group || null });
		});
	}

	fetch_form(args) {
		const load_key =
			args.docname || `new:${args.briefing_type || ""}:${args.student_group || ""}`;
		this.loading_key = load_key;

		frappe.call({
			method: "numerouno.numerouno.page.safety_briefing_form.safety_briefing_form_api.get_form_html",
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
					? `${this.doc.briefing_type} (${this.doc.name})`
					: this.doc.briefing_type;
				this.page.set_title(`${__("Safety Briefing")} — ${title}`);
			},
			error: () => {
				this.loading_key = null;
			},
		});
	}

	render(html) {
		if (!this.doc) return;

		this.$root.html(`
			<p class="sbf-toolbar-note">
				<strong>${frappe.utils.escape_html(this.doc.briefing_type || "")}</strong>
				${this.doc.form_code ? ` — ${frappe.utils.escape_html(this.doc.form_code)}` : ""}
				<br>${__("Layout matches the official Word form. Click Save to store changes.")}
			</p>
			<div class="sbf-doc-wrap">
				<div class="sbf-doc">${html}</div>
			</div>
		`);

		this.enhance_editable();
		this.init_signature_pads();
		this.apply_readonly_state();
	}

	enhance_editable() {
		const d = this.doc;
		const $doc = this.$root.find(".sbf-doc");

		// Discussion Y/N
		$doc.find(".nutc-discussion-h2s tr:not(.header-row)").each((idx, tr) => {
			const row = d.discussion_points?.[idx];
			if (!row) return;
			$(tr).find(".col-yn").html(this.yn_checkbox("discussion_points", idx, row.confirmed));
		});
		$doc.find(".nutc-discussion tr:not(:first-child)").each((idx, tr) => {
			const row = d.discussion_points?.[idx];
			if (!row) return;
			$(tr).find(".col-yn").html(this.yn_checkbox("discussion_points", idx, row.confirmed));
		});

		// Practical Y/N
		if (d.practical_items?.length) {
			const $h2sYn = $doc.find(".nutc-practical-h2s .col-yn[rowspan]").first();
			if ($h2sYn.length) {
				$h2sYn.html(this.yn_checkbox("practical_items", 0, d.practical_items[0].confirmed));
			}
			$doc.find(".nutc-practical .col-yn[rowspan]").each((idx, cell) => {
				const row = d.practical_items?.[idx];
				if (!row) return;
				$(cell).html(this.yn_checkbox("practical_items", idx, row.confirmed));
			});
		}

		// Attendees
		const module_mode = d.attendee_signature_mode === "Module Columns";
		const sign_count = module_mode
			? (d.signature_labels || "").split(",").map((s) => s.trim()).filter(Boolean).length
			: 1;

		$doc.find(".nutc-attendees tr").each((idx, tr) => {
			if ($(tr).find(".header-yellow").length) return;
			const rowIdx = $(tr).find(".col-sr").text().trim();
			const attendee_idx = cint(rowIdx) - 1;
			if (attendee_idx < 0 || attendee_idx > 15) return;
			const row = (d.attendees || [])[attendee_idx] || {};

			$(tr).find(".col-name").html(this.text_input("attendees", attendee_idx, "learner_name", row.learner_name));
			$(tr).find(".col-company").html(this.text_input("attendees", attendee_idx, "company", row.company));

			if (sign_count > 1) {
				$(tr)
					.find(".col-sign")
					.each((j, cell) => {
						const field = `sign_col_${j + 1}`;
						$(cell).html(this.module_checkbox("attendees", attendee_idx, field, row[field]));
					});
			} else {
				$(tr).find(".col-signed").html(this.signature_cell("attendees", attendee_idx, "signed", row.signed));
			}
		});

		// Single instructor (Basic H2S)
		const $singleInst = $doc.find(".nutc-instructor-single tr").eq(1);
		if ($singleInst.length && d.instructor_mode === "Single Instructor") {
			const cells = $singleInst.find("td");
			$(cells[0]).html(this.text_input_root("instructor_name", d.instructor_name));
			$(cells[1]).html(this.signature_cell_root("instructor_signature", d.instructor_signature));
			$(cells[2]).html(this.date_input("instructor_date", d.instructor_date));
		}

		// Course instructors table
		if (d.instructor_mode === "Course Instructors Table") {
			const is_tsbb = d.briefing_type === "TSbB";
			let inst_idx = -1;
			$doc.find(".nutc-instructors tr").each((_, tr) => {
				if ($(tr).find("th").length) return;
				inst_idx += 1;
				const row = (d.instructors || [])[inst_idx] || {};
				const cells = $(tr).find("td");
				if (is_tsbb) {
					$(cells[0]).html(`${inst_idx + 1}. ${this.text_input("instructors", inst_idx, "instructor_name", row.instructor_name || "")}`);
					$(cells[1]).html(this.signature_cell("instructors", inst_idx, "signature", row.signature));
				} else if (cells.length >= 3) {
					$(cells[0]).html(`${inst_idx + 1}. ${this.text_input("instructors", inst_idx, "instructor_name", row.instructor_name || "")}`);
					$(cells[1]).html(this.text_input("instructors", inst_idx, "module", row.module || "OIS -"));
					$(cells[2]).html(this.signature_cell("instructors", inst_idx, "signature", row.signature));
				}
			});
		}

		// Dates
		if (["TBOSIET", "BOSIET EBS"].includes(d.briefing_type)) {
			this.replace_date_in_cell($doc, ".nutc-dates tr:first-child td:eq(0)", "date_ff", d.date_ff, "Date (FF)");
			this.replace_date_in_cell($doc, ".nutc-dates tr:first-child td:eq(1)", "date_fa", d.date_fa, "Date (FA)");
			this.replace_date_in_cell($doc, ".nutc-dates tr:first-child td:eq(2)", "date_ss", d.date_ss, "Date (SS)");
			this.replace_date_in_cell($doc, ".nutc-dates tr:first-child td:eq(3)", "date_lb", d.date_lb, "Date (LB)");
			this.replace_date_in_cell($doc, ".nutc-dates tr:last-child td:first", "date_huet", d.date_huet, "Date (HUET)");
			if (d.briefing_type === "BOSIET EBS") {
				this.replace_date_in_cell($doc, ".nutc-dates tr:last-child td:last", "date_huet_ebs", d.date_huet_ebs, "Date (HUET EBS)");
			}
		} else {
			const $dateLine = $doc.find(".date-single");
			if ($dateLine.length) {
				$dateLine.html(`Date ${this.date_input("briefing_date", d.briefing_date)}`);
			}
		}
	}

	replace_date_in_cell($doc, selector, field, value, label) {
		const $cell = $doc.find(selector);
		if (!$cell.length) return;
		$cell.html(`${label} ${this.date_input(field, value)}`);
	}

	strip_leading_index(text, fallback) {
		if (fallback) return fallback;
		return (text || "").replace(/^\d+\.\s*/, "").trim();
	}

	yn_checkbox(table, idx, checked) {
		return `<input type="checkbox" class="sbf-yn-check" data-table="${table}" data-idx="${idx}" data-field="confirmed" ${checked ? "checked" : ""}>`;
	}

	module_checkbox(table, idx, field, checked) {
		return `<input type="checkbox" class="sbf-module-check" data-table="${table}" data-idx="${idx}" data-field="${field}" ${checked ? "checked" : ""}>`;
	}

	text_input(table, idx, field, value) {
		return `<input type="text" class="sbf-cell-input" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${frappe.utils.escape_html(value || "")}">`;
	}

	text_input_root(field, value) {
		return `<input type="text" class="sbf-cell-input" data-root="${field}" value="${frappe.utils.escape_html(value || "")}">`;
	}

	date_input(field, value) {
		return `<input type="date" class="sbf-date-input" data-root="${field}" value="${value || ""}">`;
	}

	signature_cell(table, idx, field, value) {
		const id = `sig-${table}-${idx}-${field}`.replace(/[^a-zA-Z0-9_-]/g, "_");
		const img = value ? `<img src="${value}" class="sig-img sbf-sig-preview" alt="">` : "";
		return `<div class="sbf-signature-wrap">
			${img}
			<canvas class="sbf-signature-canvas ${value ? "has-signature" : ""}" id="${id}" width="120" height="28"></canvas>
			<input type="hidden" class="sbf-signature-value" data-table="${table}" data-idx="${idx}" data-field="${field}" value="${value || ""}">
			<div class="sbf-signature-actions"><button type="button" class="sbf-sig-clear" data-target="${id}">${__("Clear")}</button></div>
		</div>`;
	}

	signature_cell_root(field, value) {
		const id = `sig-root-${field}`;
		const img = value ? `<img src="${value}" class="sig-img sbf-sig-preview" alt="">` : "";
		return `<div class="sbf-signature-wrap">
			${img}
			<canvas class="sbf-signature-canvas ${value ? "has-signature" : ""}" id="${id}" width="120" height="28"></canvas>
			<input type="hidden" class="sbf-signature-value" data-root="${field}" value="${value || ""}">
			<div class="sbf-signature-actions"><button type="button" class="sbf-sig-clear" data-target="${id}">${__("Clear")}</button></div>
		</div>`;
	}

	init_signature_pads() {
		this.$root.find(".sbf-signature-canvas").each(function () {
			const canvas = this;
			const $wrap = $(canvas).closest(".sbf-signature-wrap");
			const $hidden = $wrap.find(".sbf-signature-value");
			const ctx = canvas.getContext("2d");
			let drawing = false;

			function resize() {
				const ratio = window.devicePixelRatio || 1;
				const rect = canvas.getBoundingClientRect();
				canvas.width = Math.max(rect.width, 100) * ratio;
				canvas.height = 28 * ratio;
				ctx.setTransform(1, 0, 0, 1, 0, 0);
				ctx.scale(ratio, ratio);
				ctx.lineWidth = 1.5;
				ctx.lineCap = "round";
				ctx.strokeStyle = "#000";
			}

			function pointFromEvent(event) {
				const rect = canvas.getBoundingClientRect();
				const source = event.touches ? event.touches[0] : event;
				return { x: source.clientX - rect.left, y: source.clientY - rect.top };
			}

			function save() {
				$hidden.val(canvas.toDataURL("image/png"));
				$wrap.find(".sbf-sig-preview").remove();
				$(canvas).addClass("has-signature");
			}

			resize();
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

		this.$root.find(".sbf-sig-clear").on("click", function (e) {
			e.preventDefault();
			const id = $(this).data("target");
			const canvas = document.getElementById(id);
			if (!canvas) return;
			const $wrap = $(canvas).closest(".sbf-signature-wrap");
			const ctx = canvas.getContext("2d");
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			$wrap.find(".sbf-signature-value").val("");
			$wrap.find(".sbf-sig-preview").remove();
			$(canvas).removeClass("has-signature");
		});
	}

	apply_readonly_state() {
		const submitted = cint(this.doc?.docstatus) === 1;
		this.$root.find("input, canvas, button.sbf-sig-clear").prop("disabled", submitted);
		if (submitted) {
			this.page.clear_primary_action();
			this.$root.find(".sbf-toolbar-note").html(
				`<strong>${frappe.utils.escape_html(this.doc.briefing_type || "")}</strong> — ${__("Submitted (read-only). Use Print for the official document.")}`
			);
		} else if (!this.page.btn_primary?.length) {
			this.page.set_primary_action(__("Save"), () => this.save());
		}
	}

	collect_data() {
		const data = frappe.utils.deep_clone(this.doc) || {};

		this.$root.find("[data-root]").each(function () {
			const $el = $(this);
			const field = $el.data("root");
			if ($el.hasClass("sbf-signature-value")) {
				data[field] = $el.val();
			} else {
				data[field] = $el.val();
			}
		});

		this.$root.find(".sbf-yn-check, .sbf-module-check").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.is(":checked") ? 1 : 0;
		});

		this.$root.find(".sbf-cell-input[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.val();
		});

		this.$root.find(".sbf-signature-value[data-table]").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			if (data[table]?.[idx]) data[table][idx][field] = $el.val();
		});

		data.instructors = this.rebuild_instructors_from_dom(data.instructors || []);
		data.attendees = this.ensure_attendee_rows(data.attendees);
		return data;
	}

	rebuild_instructors_from_dom(existing) {
		if (this.doc.instructor_mode !== "Course Instructors Table") return existing;
		const is_tsbb = this.doc.briefing_type === "TSbB";
		const rows = [];
		const max_idx = Math.max(
			...this.$root
				.find('.sbf-cell-input[data-table="instructors"]')
				.map((_, el) => cint($(el).data("idx")))
				.get(),
			0
		);

		for (let i = 0; i <= max_idx; i++) {
			const row = existing[i] || {};
			rows.push({
				instructor_name:
					this.$root
						.find(`.sbf-cell-input[data-table="instructors"][data-idx="${i}"][data-field="instructor_name"]`)
						.val() || "",
				module: is_tsbb
					? row.module || ""
					: this.$root
							.find(`.sbf-cell-input[data-table="instructors"][data-idx="${i}"][data-field="module"]`)
							.val() || "",
				signature:
					this.$root
						.find(`.sbf-signature-value[data-table="instructors"][data-idx="${i}"][data-field="signature"]`)
						.val() || "",
			});
		}

		return rows.filter((row) => row.instructor_name || row.signature || (row.module && row.module !== "OIS -"));
	}

	save() {
		if (this.saving || !this.doc || cint(this.doc.docstatus) === 1) return;

		this.saving = true;
		frappe.call({
			method: "numerouno.numerouno.page.safety_briefing_form.safety_briefing_form_api.save_form",
			args: { data: this.collect_data() },
			freeze: true,
			callback: (r) => {
				this.saving = false;
				if (r.exc) return;
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				if (this.doc.name) {
					this.loading_key = null;
					frappe.set_route("safety-briefing-form", this.doc.name);
				} else {
					this.fetch_form({ briefing_type: this.doc.briefing_type, student_group: this.doc.student_group });
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
		frappe.confirm(__("Submit this Safety Briefing?"), () => {
			this.save_and_then(() => {
				frappe.call({
					method: "numerouno.numerouno.page.safety_briefing_form.safety_briefing_form_api.submit",
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
			method: "numerouno.numerouno.page.safety_briefing_form.safety_briefing_form_api.save_form",
			args: { data: this.collect_data() },
			callback: (r) => {
				if (r.exc) return;
				this.doc = r.message;
				done();
			},
		});
	}

	populate_attendees() {
		if (!this.doc?.student_group) {
			frappe.prompt(
				[{ fieldname: "student_group", label: __("Student Group"), fieldtype: "Link", options: "Student Group", reqd: 1 }],
				(values) => {
					this.doc.student_group = values.student_group;
					this.loading_key = null;
					this.fetch_attendees(values.student_group);
				},
				__("Select Student Group")
			);
			return;
		}
		this.fetch_attendees(this.doc.student_group);
	}

	fetch_attendees(student_group) {
		frappe.call({
			method: "numerouno.numerouno.doctype.safety_briefing.safety_briefing.get_attendees_for_student_group",
			args: { student_group },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				this.doc.attendees = r.message || [];
				this.doc.student_group = student_group;
				this.loading_key = null;
				const args = this.doc.name
					? { docname: this.doc.name }
					: { briefing_type: this.doc.briefing_type, student_group };
				if (this.doc.name) {
					frappe.call({
						method: "numerouno.numerouno.page.safety_briefing_form.safety_briefing_form_api.save_form",
						args: { data: { ...this.collect_data(), attendees: this.doc.attendees, student_group } },
						callback: (save_r) => {
							if (!save_r.exc) this.doc = save_r.message;
							this.fetch_form({ docname: this.doc.name });
						},
					});
				} else {
					this.fetch_form(args);
				}
				frappe.show_alert({ message: __("Attendees loaded"), indicator: "green" });
			},
		});
	}

	print_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the document before printing."));
			return;
		}
		this.save_and_then(() => frappe.set_route("print", "Safety Briefing", this.doc.name));
	}

	open_erp_form() {
		if (this.doc?.name) frappe.set_route("Form", "Safety Briefing", this.doc.name);
		else frappe.set_route("Form", "Safety Briefing", "new-safety-briefing-1");
	}

	ensure_attendee_rows(attendees) {
		const rows = (attendees || []).slice(0, 16);
		while (rows.length < 16) rows.push({});
		return rows;
	}
}
