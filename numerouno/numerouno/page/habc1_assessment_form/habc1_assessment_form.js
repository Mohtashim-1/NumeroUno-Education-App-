frappe.provide("numerouno.habc1");

function h1Escape(value) {
	if (frappe.utils && typeof frappe.utils.escape_html === "function") {
		return frappe.utils.escape_html(value || "");
	}
	return $("<div>").text(value || "").html();
}

frappe.pages["habc1-assessment-form"].on_page_load = function (wrapper) {
	if (wrapper.habc1_assessment_form) {
		return;
	}
	try {
		if (!$("#habc1-assessment-css").length) {
			$(
				'<link id="habc1-assessment-css" rel="stylesheet" type="text/css" href="/assets/numerouno/css/habc1_assessment_form.css?v=4">'
			).appendTo("head");
		}
		const page =
			wrapper.page && wrapper.page.main && wrapper.page.main.length
				? wrapper.page
				: frappe.ui.make_app_page({
						parent: wrapper,
						title: __("HABC1 Assessment Pack"),
						single_column: true,
				  });
		page.main.addClass("habc1-assessment-page");
		wrapper.habc1_assessment_form = new numerouno.habc1.Form(page);
	} catch (error) {
		console.error(error);
		$(wrapper)
			.find(".layout-main-section")
			.addBack(wrapper)
			.last()
			.html(
				`<div class="p-4">
					<h4>${__("HABC1 Assessment Pack")}</h4>
					<p class="text-danger">${__("Page failed to load. Press Ctrl+Shift+R and try again.")}</p>
				</div>`
			);
	}
};

frappe.pages["habc1-assessment-form"].on_page_show = function (wrapper) {
	if (!wrapper.habc1_assessment_form) {
		frappe.pages["habc1-assessment-form"].on_page_load(wrapper);
		return;
	}
	wrapper.habc1_assessment_form.resolve_route_and_load();
};

numerouno.habc1.Form = class {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.group = null;
		this.group_field = null;
		this.$root = $('<div class="h1-root"></div>').appendTo(this.page.main);
		this.bind_root_events();
		this.resolve_route_and_load();
	}

	bind_root_events() {
		this.$root.on("click", ".h1-load-group", (e) => {
			e.preventDefault();
			this.load_group();
		});
		this.$root.on("click", ".h1-save-btn", (e) => {
			e.preventDefault();
			this.save();
		});
		this.$root.on("click", ".h1-print-btn", (e) => {
			e.preventDefault();
			this.print_doc();
		});
		this.$root.on("click", ".h1-submit-btn", (e) => {
			e.preventDefault();
			this.submit_doc();
		});
		this.$root.on("click", ".h1-cancel-btn", (e) => {
			e.preventDefault();
			this.cancel_doc();
		});
		this.$root.on("click", ".h1-amend-btn", (e) => {
			e.preventDefault();
			this.amend_doc();
		});
		this.$root.on("click", ".h1-back-btn", (e) => {
			e.preventDefault();
			this.show_picker();
		});
		this.$root.on("click", ".h1-sign-clear", (e) => {
			e.preventDefault();
			this.clear_signature($(e.currentTarget).closest(".h1-sign-wrap"));
		});
		this.$root.on("keydown", ".h1-group-field-wrap input", (e) => {
			if (e.key === "Enter") {
				e.preventDefault();
				this.load_group();
			}
		});
	}

	resolve_route_and_load() {
		const route = frappe.get_route() || [];
		const docname = (route[1] || "").trim();
		const student_group = (frappe.route_options?.student_group || "").trim();
		if (frappe.route_options) {
			delete frappe.route_options.student_group;
		}
		if (docname) {
			this.fetch_form({ docname });
			return;
		}
		if (student_group) {
			this.fetch_form({ student_group });
			return;
		}
		if (this.doc && this.doc.name) {
			return;
		}
		this.show_picker(this.group);
	}

	show_picker(default_group = null) {
		this.doc = null;
		this.page.clear_inner_toolbar();
		this.page.set_title(__("HABC1 Assessment Pack"));
		this.page.set_primary_action(__("Open Form"), () => this.load_group());
		this.$root.html(`
			<div class="h1-portal-header">
				<div class="h1-kicker">${__("Highfield / HABC1")}</div>
				<h3>${__("Emergency First Aid Assessment Pack")}</h3>
				<p>${__("Select a student group to fill the Highfield International form. Layout matches the official paper.")}</p>
			</div>
			<div class="h1-card">
				<div class="h1-group-picker">
					<div class="h1-group-field-wrap"></div>
					<button type="button" class="h1-btn h1-btn-primary h1-load-group">${__("Open Form")}</button>
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
			parent: this.$root.find(".h1-group-field-wrap"),
			render_input: true,
		});
		this.group_field.make();
		this.group_field.refresh();
		this.$root.find(".h1-group-field-wrap .help-box").hide();
		if (default_group) {
			this.group_field.set_value(default_group);
		}
	}

	get_student_group() {
		return String(
			this.group_field?.get_value() ||
				this.group_field?.$input?.val() ||
				this.$root.find(".h1-group-field-wrap input").val() ||
				""
		).trim();
	}

	load_group() {
		const student_group = this.get_student_group();
		if (!student_group) {
			frappe.msgprint(__("Please select a Student Group"));
			return;
		}
		this.fetch_form({ student_group });
	}

	fetch_form(args) {
		frappe.call({
			method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.get_form_html",
			args,
			freeze: true,
			freeze_message: __("Loading Highfield form..."),
			callback: (r) => {
				if (r.exc) {
					return;
				}
				this.doc = r.message.doc;
				this.group = this.doc.student_group;
				this.render(r.message.html);
				if (this.doc.name) {
					frappe.router.replace_route("habc1-assessment-form", this.doc.name);
				}
			},
		});
	}

	render(html) {
		this.page.clear_primary_action();
		this.page.clear_secondary_action();
		this.page.clear_inner_toolbar();
		this.page.set_title(this.doc.name || __("HABC1 Assessment Pack"));
		const docstatus = h1Cint(this.doc.docstatus);
		const isDraft = docstatus === 0;
		const isSubmitted = docstatus === 1;
		const isCancelled = docstatus === 2;
		const isReadonly = !isDraft;

		if (isDraft) {
			this.page.set_primary_action(__("Save"), () => this.save());
			this.page.set_secondary_action(__("Print"), () => this.print_doc());
		} else {
			this.page.set_primary_action(__("Print"), () => this.print_doc());
			if (isSubmitted) {
				this.page.add_inner_button(__("Cancel"), () => this.cancel_doc(), __("Actions"));
			}
			if (isCancelled) {
				this.page.add_inner_button(__("Amend"), () => this.amend_doc(), __("Actions"));
			}
		}

		this.$root.html(`
			${this.status_banner(docstatus)}
			<div class="h1-form-bar">
				<button type="button" class="h1-btn h1-back-btn">${__("Change Group")}</button>
				<div class="h1-form-bar-meta">
					<strong>${h1Escape(this.doc.form_title || this.doc.student_group || "")}</strong>
					<span>${h1Escape(this.doc.name || "")}</span>
				</div>
				<button type="button" class="h1-btn h1-print-btn">${__("Print")}</button>
				${isSubmitted ? `<button type="button" class="h1-btn h1-cancel-btn">${__("Cancel")}</button>` : ""}
				${isCancelled ? `<button type="button" class="h1-btn h1-amend-btn">${__("Amend")}</button>` : ""}
				<button type="button" class="h1-btn h1-submit-btn" ${isDraft ? "" : "disabled"}>${__("Submit")}</button>
				<button type="button" class="h1-btn h1-btn-primary h1-save-btn" ${isDraft ? "" : "disabled"}>${__("Save")}</button>
			</div>
			<div class="h1-paper-wrap ${isReadonly ? "is-readonly" : ""}">${html}</div>
		`);
		this.init_signature_canvases();
		if (isReadonly) {
			this.$root.find("input, textarea, button.h1-sign-clear").prop("disabled", true);
		}
	}

	status_info(docstatus) {
		const ds = h1Cint(docstatus);
		if (ds === 1) {
			return {
				label: __("Submitted"),
				cls: "is-submitted",
				note: __("Submitted (read-only). Cancel, then Amend to edit."),
			};
		}
		if (ds === 2) {
			return {
				label: __("Cancelled"),
				cls: "is-cancelled",
				note: __("Cancelled. Use Amend to create an editable copy."),
			};
		}
		return {
			label: __("Draft"),
			cls: "is-draft",
			note: __("Draft — save and submit when complete."),
		};
	}

	status_banner(docstatus) {
		const info = this.status_info(docstatus);
		return `<div class="h1-status-banner ${info.cls}" role="status">
			<strong>${h1Escape(info.label)}</strong>
			<span>${h1Escape(info.note)}</span>
		</div>`;
	}

	collect() {
		const data = Object.assign({}, this.doc);
		this.$root.find(".h1-input[data-field]").each((_, el) => {
			const $el = $(el);
			data[$el.data("field")] = $el.val();
		});
		const bySr = {};
		(this.doc.learners || []).forEach((row) => {
			bySr[String(row.sr_no)] = Object.assign({}, row);
		});
		this.$root.find("[data-row-field]").each((_, el) => {
			const $el = $(el);
			const sr = String($el.data("sr"));
			if (!bySr[sr]) {
				bySr[sr] = { sr_no: h1Cint(sr) };
			}
			const field = $el.data("row-field");
			if ($el.attr("type") === "checkbox") {
				bySr[sr][field] = $el.is(":checked") ? 1 : 0;
			} else if ($el.attr("type") === "radio") {
				if ($el.is(":checked")) {
					bySr[sr][field] = $el.val();
				}
			} else {
				bySr[sr][field] = $el.val();
			}
		});
		data.learners = Object.keys(bySr)
			.sort((a, b) => h1Cint(a) - h1Cint(b))
			.map((key) => bySr[key]);
		this.$root.find('input[data-field="blended_learning"]').each((_, el) => {
			data.blended_learning = $(el).is(":checked") ? 1 : 0;
		});
		const refs = {};
		this.$root.find("[data-ref-field]").each((_, el) => {
			const $el = $(el);
			const idx = String($el.data("ref"));
			if (!refs[idx]) {
				refs[idx] = {};
			}
			refs[idx][$el.data("ref-field")] = $el.val();
		});
		data.referrals = Object.keys(refs)
			.sort((a, b) => h1Cint(a) - h1Cint(b))
			.map((key) => refs[key]);
		return data;
	}

	save() {
		if (h1Cint(this.doc.docstatus) !== 0) {
			frappe.msgprint(__("Submitted form cannot be edited"));
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.save_form_data",
			args: { data: this.collect() },
			freeze: true,
			freeze_message: __("Saving..."),
			callback: (r) => {
				if (r.exc) {
					return;
				}
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved {0}", [this.doc.name]), indicator: "green" });
				frappe.router.replace_route("habc1-assessment-form", this.doc.name);
			},
		});
	}

	submit_doc() {
		if (!this.doc || !this.doc.name) {
			this.save();
			return;
		}
		frappe.confirm(__("Submit this HABC1 assessment pack?"), () => {
			this.save_then(() => {
				frappe.call({
					method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.submit_form",
					args: { docname: this.doc.name },
					freeze: true,
					callback: (r) => {
						if (r.exc) {
							return;
						}
						this.fetch_form({ docname: this.doc.name });
					},
				});
			});
		});
	}

	save_then(fn) {
		frappe.call({
			method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.save_form_data",
			args: { data: this.collect() },
			freeze: true,
			callback: (r) => {
				if (r.exc) {
					return;
				}
				this.doc = r.message;
				fn();
			},
		});
	}

	cancel_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the form first."));
			return;
		}
		if (h1Cint(this.doc.docstatus) !== 1) {
			frappe.msgprint(__("Only a submitted HABC1 Assessment Pack can be cancelled."));
			return;
		}
		frappe.confirm(
			__("Cancel this HABC1 Assessment Pack? Use Amend afterwards to create an editable copy."),
			() => {
				frappe.call({
					method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.cancel_form",
					args: { docname: this.doc.name },
					freeze: true,
					freeze_message: __("Cancelling..."),
					callback: (r) => {
						if (r.exc) {
							return;
						}
						frappe.show_alert({ message: __("Cancelled"), indicator: "orange" });
						this.fetch_form({ docname: this.doc.name });
					},
				});
			}
		);
	}

	amend_doc() {
		if (!this.doc?.name) {
			frappe.msgprint(__("Please save the form first."));
			return;
		}
		if (h1Cint(this.doc.docstatus) !== 2) {
			frappe.msgprint(__("Cancel the HABC1 Assessment Pack first, then Amend."));
			return;
		}
		frappe.confirm(__("Create an editable copy with the same data?"), () => {
			frappe.call({
				method: "numerouno.numerouno.page.habc1_assessment_form.habc1_assessment_form.amend_form",
				args: { docname: this.doc.name },
				freeze: true,
				freeze_message: __("Creating amended copy..."),
				callback: (r) => {
					if (r.exc) {
						return;
					}
					const name = r.message?.name;
					if (!name) {
						frappe.msgprint(__("Amend did not return a new document."));
						return;
					}
					frappe.show_alert({ message: __("Amended as {0}", [name]), indicator: "green" });
					frappe.set_route("habc1-assessment-form", name);
				},
			});
		});
	}

	print_doc() {
		if (!this.doc || !this.doc.name) {
			frappe.msgprint(__("Save the form before printing"));
			return;
		}
		const open_print = () => {
			window.open(
				frappe.urllib.get_full_url(
					"/printview?doctype=" +
						encodeURIComponent("HABC1 Assessment Pack") +
						"&name=" +
						encodeURIComponent(this.doc.name) +
						"&format=" +
						encodeURIComponent("HABC1 Assessment Pack") +
						"&no_letterhead=1"
				),
				"_blank"
			);
		};
		if (h1Cint(this.doc.docstatus) === 1) {
			open_print();
			return;
		}
		this.save_then(open_print);
	}

	init_signature_canvases() {
		this.$root.find(".h1-sign-canvas").each((_, canvas) => {
			this.bind_signature_canvas(canvas);
		});
	}

	bind_signature_canvas(canvas) {
		if (!canvas || canvas.dataset.bound === "1") {
			return;
		}
		canvas.dataset.bound = "1";
		const ctx = canvas.getContext("2d");
		ctx.strokeStyle = "#111";
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
		const end = () => {
			if (!drawing) {
				return;
			}
			drawing = false;
			const $wrap = $(canvas).closest(".h1-sign-wrap");
			$wrap.find("input[data-field], input[data-row-field]").val(canvas.toDataURL("image/png"));
			$wrap.find("img").remove();
		};
		canvas.addEventListener("mousedown", start);
		canvas.addEventListener("mousemove", move);
		window.addEventListener("mouseup", end);
		canvas.addEventListener("touchstart", start, { passive: false });
		canvas.addEventListener("touchmove", move, { passive: false });
		canvas.addEventListener("touchend", end);
	}

	clear_signature($wrap) {
		const canvas = $wrap.find("canvas").get(0);
		if (canvas) {
			const ctx = canvas.getContext("2d");
			ctx.clearRect(0, 0, canvas.width, canvas.height);
		}
		$wrap.find("img").remove();
		$wrap.find("input[data-field], input[data-row-field]").val("");
	}
};

function h1Cint(value) {
	if (typeof window.cint === "function") {
		return window.cint(value);
	}
	const parsed = parseInt(value, 10);
	return Number.isNaN(parsed) ? 0 : parsed;
}
