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
		this.page.clear_inner_toolbar();
		this.page.set_primary_action(__("Save"), () => this.save());
		this.page.add_inner_button(__("Print"), () => this.print_doc(), __("Actions"));
		this.page.add_inner_button(__("Submit"), () => this.submit_doc(), __("Actions"));
		this.page.add_inner_button(__("Cancel"), () => this.cancel_doc(), __("Actions"));
		this.page.add_inner_button(__("Amend"), () => this.amend_doc(), __("Actions"));
		this.page.add_inner_button(__("Populate Attendees"), () => this.populate_attendees(), __("Actions"));
		this.page.add_inner_button(__("Add Instructor Row"), () => this.add_instructor_row(), __("Actions"));
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

		const proceed = () => {
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
		};

		if (!args.docname && args.briefing_type && args.student_group) {
			frappe.call({
				method: "numerouno.numerouno.utils.form_duplicate_guard.check_existing_course_form",
				args: {
					form_kind: "safety_briefing",
					student_group: args.student_group,
					form_type: args.briefing_type,
				},
				callback: (r) => {
					if (r.exc) {
						this.loading_key = null;
						return;
					}
					if (r.message?.exists) {
						this.loading_key = null;
						this.show_existing_form_message(r.message, "Safety Briefing");
						return;
					}
					proceed();
				},
				error: () => {
					this.loading_key = null;
				},
			});
			return;
		}

		proceed();
	}

	show_existing_form_message(payload, label) {
		const url = payload.url || `/app/safety-briefing-form/${payload.name}`;
		frappe.msgprint({
			title: __("{0} Already Exists", [label]),
			indicator: "orange",
			message: `
				<p>${frappe.utils.escape_html(
					__("A form already exists for this student group ({0}).", [payload.name])
				)}</p>
				<p><a class="btn btn-primary btn-sm" href="${frappe.utils.escape_html(url)}">${__(
					"Open {0}",
					[payload.name]
				)}</a></p>
			`,
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

		if (d.briefing_type === "Basic H2S") {
			const $codes = $doc.find(".h2s-course-codes");
			if ($codes.length) {
				$codes.html(`
					<label class="sbf-variant-check">
						<input type="checkbox" class="sbf-variant-check-input" data-root="variant_9014" ${d.variant_9014 ? "checked" : ""}>
						<span>9014 –</span>
					</label>
					<label class="sbf-variant-check">
						<input type="checkbox" class="sbf-variant-check-input" data-root="variant_9014_a" ${d.variant_9014_a ? "checked" : ""}>
						<span>9014 – A</span>
					</label>
					<label class="sbf-variant-check">
						<input type="checkbox" class="sbf-variant-check-input" data-root="variant_9014_b" ${d.variant_9014_b ? "checked" : ""}>
						<span>9014 – B</span>
					</label>
				`);
			}
		}

		// Discussion Y / N columns
		$doc.find(".nutc-discussion-h2s tr:not(.header-row)").each((idx, tr) => {
			const row = d.discussion_points?.[idx];
			if (!row) return;
			const boxes = this.yn_checkboxes("discussion_points", idx, row);
			$(tr).find(".col-y").html(boxes.y);
			$(tr).find(".col-n").html(boxes.n);
		});
		$doc.find(".nutc-discussion tr:not(:first-child)").each((idx, tr) => {
			const row = d.discussion_points?.[idx];
			if (!row) return;
			const boxes = this.yn_checkboxes("discussion_points", idx, row);
			$(tr).find(".col-y").html(boxes.y);
			$(tr).find(".col-n").html(boxes.n);
		});

		// Practical Y / N columns
		if (d.practical_items?.length) {
			const $h2sY = $doc.find(".nutc-practical-h2s .col-y[rowspan]").first();
			const $h2sN = $doc.find(".nutc-practical-h2s .col-n[rowspan]").first();
			if ($h2sY.length && $h2sN.length) {
				const boxes = this.yn_checkboxes("practical_items", 0, d.practical_items[0]);
				$h2sY.html(boxes.y);
				$h2sN.html(boxes.n);
			}
			$doc.find(".nutc-practical .col-y[rowspan]").each((idx, cell) => {
				const row = d.practical_items?.[idx];
				if (!row) return;
				const boxes = this.yn_checkboxes("practical_items", idx, row);
				$(cell).html(boxes.y);
				$(cell).siblings(".col-n[rowspan]").html(boxes.n);
			});
		}

		this.bind_yn_exclusivity($doc);

		// Attendees
		const module_mode = d.attendee_signature_mode === "Module Columns";
		const sign_count = module_mode
			? (d.signature_labels || "").split(",").map((s) => s.trim()).filter(Boolean).length
			: 1;
		$doc.find(".nutc-attendees").toggleClass("module-signatures", sign_count > 1);

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
						// Module columns (FF/FA/SS/HUET/LB) are learner signatures, not checkboxes.
						const raw = row[field];
						const value = raw && String(raw) !== "0" && String(raw) !== "1" ? raw : "";
						$(cell).html(this.signature_cell("attendees", attendee_idx, field, value, { compact: true }));
					});
			} else {
				$(tr).find(".col-signed").html(this.signature_cell("attendees", attendee_idx, "signed", row.signed, { compact: true }));
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
					$(cells[1]).html(this.text_input("instructors", inst_idx, "module", row.module || "OIS"));
					$(cells[2]).html(this.signature_cell("instructors", inst_idx, "signature", row.signature, { compact: true }));
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

	yn_checkboxes(table, idx, row) {
		const yChecked = cint(row?.confirmed);
		const nChecked = cint(row?.denied);
		return {
			y: `<input type="checkbox" class="sbf-yn-check sbf-yn-y" data-table="${table}" data-idx="${idx}" data-field="confirmed" ${yChecked ? "checked" : ""}>`,
			n: `<input type="checkbox" class="sbf-yn-check sbf-yn-n" data-table="${table}" data-idx="${idx}" data-field="denied" ${nChecked ? "checked" : ""}>`,
		};
	}

	bind_yn_exclusivity($doc) {
		$doc.find(".sbf-yn-y").off("change.sbfYn").on("change.sbfYn", function () {
			if (this.checked) {
				$(this).closest("tr").find(".sbf-yn-n").prop("checked", false);
			}
		});
		$doc.find(".sbf-yn-n").off("change.sbfYn").on("change.sbfYn", function () {
			if (this.checked) {
				$(this).closest("tr").find(".sbf-yn-y").prop("checked", false);
			}
		});
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
		const display = format_sbf_date_display(value);
		return `<input type="text" class="sbf-date-input" data-root="${field}" inputmode="numeric" placeholder="dd-mm-yyyy" value="${frappe.utils.escape_html(display)}">`;
	}

	signature_cell(table, idx, field, value, opts = {}) {
		return render_signature_field({
			value: value,
			table: table,
			idx: idx,
			field: field,
			compact: !!(opts && opts.compact),
		});
	}

	signature_cell_root(field, value) {
		return render_signature_field({
			value: value,
			root: field,
		});
	}

	init_signature_pads() {
		const self = this;
		this.$root.find(".sbf-sig-open-btn").off("click").on("click", function (e) {
			e.preventDefault();
			if (self.doc && cint(self.doc.docstatus) === 1) return;
			open_safety_briefing_signature_modal($(this).closest(".sbf-signature-wrap"));
		});

		this.$root.find(".sbf-sig-clear").off("click").on("click", function (e) {
			e.preventDefault();
			if (self.doc && cint(self.doc.docstatus) === 1) return;
			clear_safety_briefing_signature($(this).closest(".sbf-signature-wrap"));
		});

		this.$root.find(".sbf-signature-box").off("click").on("click", function (e) {
			if ($(e.target).closest("button").length) return;
			if (self.doc && cint(self.doc.docstatus) === 1) return;
			open_safety_briefing_signature_modal($(this).closest(".sbf-signature-wrap"));
		});
	}

	apply_readonly_state() {
		const ds = cint(this.doc?.docstatus);
		const locked = ds === 1 || ds === 2;
		this.$root.find("input, select, textarea, button.sbf-sig-open-btn, button.sbf-sig-clear").prop("disabled", locked);
		this.$root.find(".sbf-signature-box").toggleClass("sbf-signature-readonly", locked);
		if (ds === 1) {
			this.page.clear_primary_action();
			this.$root.find(".sbf-toolbar-note").html(
				`<strong>${frappe.utils.escape_html(this.doc.briefing_type || "")}</strong> — ${__("Submitted (read-only). Cancel then Amend to edit signatures.")}`
			);
		} else if (ds === 2) {
			this.page.clear_primary_action();
			this.$root.find(".sbf-toolbar-note").html(
				`<strong>${frappe.utils.escape_html(this.doc.briefing_type || "")}</strong> — ${__("Cancelled. Use Amend to create an editable copy.")}`
			);
		} else if (!this.page.btn_primary?.length) {
			this.page.set_primary_action(__("Save"), () => this.save());
		}
	}

	collect_data() {
		const data = frappe.utils.deep_clone(this.doc) || {};

		const date_fields = [
			"briefing_date",
			"date_ff",
			"date_fa",
			"date_ss",
			"date_lb",
			"date_huet",
			"date_huet_ebs",
			"instructor_date",
		];
		this.$root.find("[data-root]").each(function () {
			const $el = $(this);
			const field = $el.data("root");
			if ($el.hasClass("sbf-signature-value")) {
				data[field] = $el.val();
			} else if ($el.hasClass("sbf-date-input") || date_fields.includes(field)) {
				data[field] = parse_sbf_date_value($el.val());
			} else {
				data[field] = $el.val();
			}
		});

		this.$root.find(".sbf-yn-check, .sbf-module-check, .sbf-variant-check-input").each(function () {
			const $el = $(this);
			const table = $el.data("table");
			const idx = cint($el.data("idx"));
			const field = $el.data("field");
			const root = $el.data("root");
			if (root) {
				data[root] = $el.is(":checked") ? 1 : 0;
				return;
			}
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

		return rows.filter((row) => row.instructor_name || row.signature || (row.module && row.module !== "OIS" && row.module !== "OIS -"));
	}

	add_instructor_row() {
		if (!this.doc || this.doc.instructor_mode !== "Course Instructors Table") {
			frappe.msgprint(__("Instructor rows are not used for this briefing type."));
			return;
		}
		if (cint(this.doc.docstatus) === 1) {
			frappe.msgprint(__("Submitted briefing is read-only."));
			return;
		}

		const $table = this.$root.find(".nutc-instructors");
		if (!$table.length) return;

		const is_tsbb = this.doc.briefing_type === "TSbB";
		const current_count = $table.find("tr").filter((_, tr) => !$(tr).find("th").length).length;
		const idx = current_count;

		const name_cell = `${idx + 1}. ${this.text_input("instructors", idx, "instructor_name", "")}`;
		const sign_cell = this.signature_cell("instructors", idx, "signature", "", { compact: true });
		const row_html = is_tsbb
			? `<tr><td>${name_cell}</td><td>${sign_cell}</td></tr>`
			: `<tr><td>${name_cell}</td><td>${this.text_input("instructors", idx, "module", "OIS")}</td><td>${sign_cell}</td></tr>`;

		$table.append(row_html);
		this.init_signature_pads();
		this.apply_readonly_state();
		frappe.show_alert({ message: __("Instructor row added"), indicator: "green" });
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

	merge_attendees_preserving_signatures(incoming) {
		const existing = this.doc.attendees || [];
		const by_student = {};
		const by_name = {};
		existing.forEach((row) => {
			const norm = (v) => {
				const s = (v == null ? "" : String(v)).trim();
				if (!s || s === "0") return "";
				if (s === "1") return "1"; // legacy checkbox
				return s;
			};
			const payload = {
				signed: norm(row.signed),
				sign_col_1: norm(row.sign_col_1),
				sign_col_2: norm(row.sign_col_2),
				sign_col_3: norm(row.sign_col_3),
				sign_col_4: norm(row.sign_col_4),
				sign_col_5: norm(row.sign_col_5),
			};
			const has =
				payload.signed ||
				payload.sign_col_1 ||
				payload.sign_col_2 ||
				payload.sign_col_3 ||
				payload.sign_col_4 ||
				payload.sign_col_5;
			if (!has) return;
			if (row.student) by_student[row.student] = payload;
			const name = (row.learner_name || "").trim().toLowerCase();
			if (name) by_name[name] = payload;
		});
		return (incoming || []).map((row) => {
			const student = (row.student || "").trim();
			const name = (row.learner_name || "").trim().toLowerCase();
			const prev = (student && by_student[student]) || (name && by_name[name]) || {};
			return { ...row, ...prev };
		});
	}

	fetch_attendees(student_group) {
		const run = () => {
			frappe.call({
				method: "numerouno.numerouno.doctype.safety_briefing.safety_briefing.get_attendees_for_student_group",
				args: { student_group },
				freeze: true,
				callback: (r) => {
					if (r.exc) return;
					this.doc.attendees = this.merge_attendees_preserving_signatures(r.message || []);
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
		};

		const has_sigs = (this.doc.attendees || []).some((row) => {
			const vals = [row.signed, row.sign_col_1, row.sign_col_2, row.sign_col_3, row.sign_col_4, row.sign_col_5];
			return vals.some((v) => {
				const s = (v == null ? "" : String(v)).trim();
				return s && s !== "0";
			});
		});
		if (has_sigs) {
			frappe.confirm(
				__("Reload attendees from Student Group? Existing learner signatures will be kept where names match."),
				run
			);
		} else {
			run();
		}
	}

	print_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the document before printing."));
			return;
		}
		this.save_and_then(() => frappe.set_route("print", "Safety Briefing", this.doc.name));
	}

	open_erp_form() {
		frappe.route_options = { stay_on_erp_form: 1 };
		if (this.doc?.name) frappe.set_route("Form", "Safety Briefing", this.doc.name);
		else frappe.set_route("Form", "Safety Briefing", "new-safety-briefing-1");
	}

	ensure_attendee_rows(attendees) {
		const rows = (attendees || []).slice(0, 16);
		while (rows.length < 16) rows.push({});
		return rows;
	}
}


function format_sbf_date_display(value) {
	if (!value) return "";
	const raw = String(value).trim();
	// already dd-mm-yyyy
	if (/^\d{2}-\d{2}-\d{4}$/.test(raw)) return raw;
	// yyyy-mm-dd from backend
	if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
		const [y, m, d] = raw.slice(0, 10).split("-");
		return `${d}-${m}-${y}`;
	}
	try {
		return frappe.datetime.str_to_user(raw);
	} catch (e) {
		return raw;
	}
}

function parse_sbf_date_value(value) {
	const raw = String(value || "").trim();
	if (!raw) return null;
	if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
	const m = raw.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
	if (m) {
		const d = m[1].padStart(2, "0");
		const mo = m[2].padStart(2, "0");
		const y = m[3];
		return `${y}-${mo}-${d}`;
	}
	return raw;
}

function render_signature_field(config) {
	const value = config.value || "";
	const hasSig = !!value;
	const compact = !!config.compact;
	const attrs = config.root
		? `data-root="${frappe.utils.escape_html(config.root)}"`
		: `data-table="${frappe.utils.escape_html(config.table)}" data-idx="${config.idx}" data-field="${frappe.utils.escape_html(config.field)}"`;
	const preview = hasSig
		? `<img src="${value}" class="sbf-sig-display" alt="${__("Signature")}">`
		: `<span class="sbf-sig-placeholder-text">${compact ? __("Sign") : __("Tap to sign")}</span>`;

	const actions = compact
		? `<button type="button" class="btn btn-default btn-xs sbf-sig-clear sbf-sig-clear-icon" title="${__("Clear")}" ${hasSig ? "" : "disabled"}>×</button>`
		: `<div class="sbf-signature-actions">
				<button type="button" class="btn btn-primary btn-xs sbf-sig-open-btn">${__("Sign")}</button>
				<button type="button" class="btn btn-default btn-xs sbf-sig-clear" ${hasSig ? "" : "disabled"}>${__("Clear")}</button>
			</div>`;

	return `
		<div class="sbf-signature-wrap ${compact ? "sbf-signature-compact" : ""}">
			<div class="sbf-signature-box ${hasSig ? "has-signature" : ""}">
				${preview}
			</div>
			<input type="hidden" class="sbf-signature-value" ${attrs} value="${frappe.utils.escape_html(value)}">
			${actions}
		</div>
	`;
}

function update_safety_briefing_signature_preview($wrap, dataUrl) {
	const $hidden = $wrap.find(".sbf-signature-value");
	const $box = $wrap.find(".sbf-signature-box");
	$hidden.val(dataUrl || "");
	const compact = $wrap.hasClass("sbf-signature-compact");
	if (dataUrl) {
		$box.addClass("has-signature").html(`<img src="${dataUrl}" class="sbf-sig-display" alt="${__("Signature")}">`);
		$wrap.find(".sbf-sig-clear").prop("disabled", false);
	} else {
		$box.removeClass("has-signature").html(
			`<span class="sbf-sig-placeholder-text">${compact ? __("Sign") : __("Tap to sign")}</span>`
		);
		$wrap.find(".sbf-sig-clear").prop("disabled", true);
	}
}

function clear_safety_briefing_signature($wrap) {
	update_safety_briefing_signature_preview($wrap, "");
}

function open_safety_briefing_signature_modal($wrap) {
	const existing = $wrap.find(".sbf-signature-value").val() || "";
	const dialog = new frappe.ui.Dialog({
		title: __("Signature"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "signature_pad_html",
			},
		],
		primary_action_label: __("Save Signature"),
		primary_action: function () {
			const canvas = dialog.$wrapper.find(".sbf-signature-modal-canvas")[0];
			if (!canvas || is_safety_briefing_canvas_blank(canvas)) {
				frappe.msgprint(__("Please draw your signature first."));
				return;
			}
			update_safety_briefing_signature_preview($wrap, canvas.toDataURL("image/png"));
			dialog.hide();
			frappe.show_alert({ message: __("Signature saved"), indicator: "green" });
		},
	});

	dialog.fields_dict.signature_pad_html.$wrapper.html(`
		<div class="sbf-signature-modal-wrap">
			<p class="sbf-signature-modal-help">${__("Draw your signature in the box below. Works with finger on tablet and phone.")}</p>
			<canvas class="sbf-signature-modal-canvas" width="560" height="200"></canvas>
			<div class="sbf-signature-modal-actions">
				<button type="button" class="btn btn-default btn-sm sbf-modal-sig-clear">${__("Clear")}</button>
			</div>
		</div>
	`);

	const canvas = dialog.fields_dict.signature_pad_html.$wrapper.find(".sbf-signature-modal-canvas")[0];
	const teardown = bind_safety_briefing_signature_canvas(canvas);

	dialog.fields_dict.signature_pad_html.$wrapper.find(".sbf-modal-sig-clear").on("click", function (e) {
		e.preventDefault();
		teardown.clear();
	});

	if (existing) {
		teardown.load(existing);
	}

	dialog.onhide = function () {
		teardown.destroy();
	};

	dialog.show();
}

function is_safety_briefing_canvas_blank(canvas) {
	const ctx = canvas.getContext("2d");
	const pixels = new Uint32Array(ctx.getImageData(0, 0, canvas.width, canvas.height).data.buffer);
	return !pixels.some((color) => color !== 0);
}

function bind_safety_briefing_signature_canvas(canvas) {
	const ctx = canvas.getContext("2d");
	let drawing = false;
	const ratio = window.devicePixelRatio || 1;
	const displayWidth = 560;
	const displayHeight = 200;

	canvas.style.width = `${displayWidth}px`;
	canvas.style.height = `${displayHeight}px`;
	canvas.width = displayWidth * ratio;
	canvas.height = displayHeight * ratio;
	ctx.setTransform(1, 0, 0, 1, 0, 0);
	ctx.scale(ratio, ratio);
	ctx.lineWidth = 2.5;
	ctx.lineCap = "round";
	ctx.lineJoin = "round";
	ctx.strokeStyle = "#111";

	function pointFromEvent(event) {
		const rect = canvas.getBoundingClientRect();
		const source =
			(event.touches && event.touches[0]) ||
			(event.changedTouches && event.changedTouches[0]) ||
			event;
		return { x: source.clientX - rect.left, y: source.clientY - rect.top };
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
	}

	function endDraw(event) {
		if (event.cancelable) event.preventDefault();
		drawing = false;
	}

	const handlers = [
		["mousedown", startDraw],
		["mousemove", draw],
		["mouseup", endDraw],
		["mouseleave", endDraw],
		["touchstart", startDraw, { passive: false }],
		["touchmove", draw, { passive: false }],
		["touchend", endDraw, { passive: false }],
		["touchcancel", endDraw, { passive: false }],
	];

	handlers.forEach(([name, fn, opts]) => canvas.addEventListener(name, fn, opts || false));

	return {
		clear() {
			ctx.clearRect(0, 0, displayWidth, displayHeight);
		},
		load(dataUrl) {
			const img = new Image();
			img.onload = function () {
				ctx.clearRect(0, 0, displayWidth, displayHeight);
				ctx.drawImage(img, 0, 0, displayWidth, displayHeight);
			};
			img.src = dataUrl;
		},
		destroy() {
			handlers.forEach(([name, fn, opts]) => canvas.removeEventListener(name, fn, opts || false));
		},
	};
}
