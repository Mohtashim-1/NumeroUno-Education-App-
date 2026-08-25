frappe.provide("numerouno.habc2");

function h2Escape(value) {
	if (frappe.utils && typeof frappe.utils.escape_html === "function") {
		return frappe.utils.escape_html(value || "");
	}
	return $("<div>").text(value || "").html();
}

frappe.pages["habc2-examination-form"].on_page_load = function (wrapper) {
	if (wrapper.habc2_examination_form) {
		return;
	}
	try {
		if (!$("#habc2-examination-css").length) {
			$(
				'<link id="habc2-examination-css" rel="stylesheet" type="text/css" href="/assets/numerouno/css/habc2_examination_form.css?v=3">'
			).appendTo("head");
		}
		const page =
			wrapper.page && wrapper.page.main && wrapper.page.main.length
				? wrapper.page
				: frappe.ui.make_app_page({
						parent: wrapper,
						title: __("HABC2 Examination Declaration"),
						single_column: true,
				  });
		page.main.addClass("habc2-examination-page");
		wrapper.habc2_examination_form = new numerouno.habc2.Form(page);
	} catch (error) {
		console.error(error);
		$(wrapper)
			.find(".layout-main-section")
			.addBack(wrapper)
			.last()
			.html(
				`<div class="p-4">
					<h4>${__("HABC2 Examination Declaration")}</h4>
					<p class="text-danger">${__("Page failed to load. Press Ctrl+Shift+R and try again.")}</p>
				</div>`
			);
	}
};

frappe.pages["habc2-examination-form"].on_page_show = function (wrapper) {
	if (!wrapper.habc2_examination_form) {
		frappe.pages["habc2-examination-form"].on_page_load(wrapper);
		return;
	}
	wrapper.habc2_examination_form.resolve_route_and_load();
};

numerouno.habc2.Form = class {
	constructor(page) {
		this.page = page;
		this.doc = null;
		this.group = null;
		this.group_field = null;
		this.$root = $('<div class="h2-root"></div>').appendTo(this.page.main);
		this.bind_root_events();
		this.resolve_route_and_load();
	}

	bind_root_events() {
		this.$root.on("click", ".h2-load-group", (e) => {
			e.preventDefault();
			this.load_group();
		});
		this.$root.on("click", ".h2-save-btn", (e) => {
			e.preventDefault();
			this.save();
		});
		this.$root.on("click", ".h2-print-btn", (e) => {
			e.preventDefault();
			this.print_doc();
		});
		this.$root.on("click", ".h2-submit-btn", (e) => {
			e.preventDefault();
			this.submit_doc();
		});
		this.$root.on("click", ".h2-back-btn", (e) => {
			e.preventDefault();
			this.show_picker();
		});
		this.$root.on("click", ".h2-sign-clear", (e) => {
			e.preventDefault();
			this.clear_signature($(e.currentTarget).closest(".h2-sign-wrap"));
		});
		this.$root.on("keydown", ".h2-group-field-wrap input", (e) => {
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
		this.page.set_title(__("HABC2 Examination Declaration"));
		this.page.set_primary_action(__("Open Form"), () => this.load_group());
		this.$root.html(`
			<div class="h2-portal-header">
				<div class="h2-kicker">${__("Highfield / HABC2")}</div>
				<h3>${__("Examination Declaration and Learner List")}</h3>
				<p>${__("Select a student group to fill the Highfield International form. Layout matches the official paper.")}</p>
			</div>
			<div class="h2-card">
				<div class="h2-group-picker">
					<div class="h2-group-field-wrap"></div>
					<button type="button" class="h2-btn h2-btn-primary h2-load-group">${__("Open Form")}</button>
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
			parent: this.$root.find(".h2-group-field-wrap"),
			render_input: true,
		});
		this.group_field.make();
		this.group_field.refresh();
		this.$root.find(".h2-group-field-wrap .help-box").hide();
		if (default_group) {
			this.group_field.set_value(default_group);
		}
	}

	get_student_group() {
		return String(
			this.group_field?.get_value() ||
				this.group_field?.$input?.val() ||
				this.$root.find(".h2-group-field-wrap input").val() ||
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
			method: "numerouno.numerouno.page.habc2_examination_form.habc2_examination_form.get_form_html",
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
					frappe.router.replace_route("habc2-examination-form", this.doc.name);
				}
			},
		});
	}

	render(html) {
		this.page.clear_primary_action();
		this.page.set_title(this.doc.name || __("HABC2 Examination Declaration"));
		this.page.set_primary_action(__("Save"), () => this.save());
		this.page.set_secondary_action(__("Print"), () => this.print_doc());
		const submitted = h2Cint(this.doc.docstatus) === 1;
		this.$root.html(`
			<div class="h2-form-bar">
				<button type="button" class="h2-btn h2-back-btn">${__("Change Group")}</button>
				<div class="h2-form-bar-meta">
					<strong>${h2Escape(this.doc.qualification_unit_title || this.doc.student_group || "")}</strong>
					<span>${h2Escape(this.doc.name || "")}</span>
				</div>
				<button type="button" class="h2-btn h2-print-btn">${__("Print")}</button>
				<button type="button" class="h2-btn h2-submit-btn" ${submitted ? "disabled" : ""}>${__("Submit")}</button>
				<button type="button" class="h2-btn h2-btn-primary h2-save-btn" ${submitted ? "disabled" : ""}>${__("Save")}</button>
			</div>
			<div class="h2-paper-wrap ${submitted ? "is-readonly" : ""}">${html}</div>
		`);
		this.init_signature_canvases();
		if (submitted) {
			this.$root.find("input, textarea, button.h2-sign-clear").prop("disabled", true);
		}
	}

	collect() {
		const data = Object.assign({}, this.doc);
		this.$root.find(".h2-input[data-field]").each((_, el) => {
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
				bySr[sr] = { sr_no: h2Cint(sr) };
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
			.sort((a, b) => h2Cint(a) - h2Cint(b))
			.map((key) => bySr[key]);
		return data;
	}

	save() {
		if (h2Cint(this.doc.docstatus) === 1) {
			frappe.msgprint(__("Submitted form cannot be edited"));
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.page.habc2_examination_form.habc2_examination_form.save_form_data",
			args: { data: this.collect() },
			freeze: true,
			freeze_message: __("Saving..."),
			callback: (r) => {
				if (r.exc) {
					return;
				}
				this.doc = r.message;
				frappe.show_alert({ message: __("Saved {0}", [this.doc.name]), indicator: "green" });
				frappe.router.replace_route("habc2-examination-form", this.doc.name);
			},
		});
	}

	submit_doc() {
		if (!this.doc || !this.doc.name) {
			this.save();
			return;
		}
		frappe.confirm(__("Submit this Highfield declaration?"), () => {
			this.save_then(() => {
				frappe.call({
					method: "numerouno.numerouno.page.habc2_examination_form.habc2_examination_form.submit_form",
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
			method: "numerouno.numerouno.page.habc2_examination_form.habc2_examination_form.save_form_data",
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

	print_doc() {
		if (!this.doc || !this.doc.name) {
			frappe.msgprint(__("Save the form before printing"));
			return;
		}
		this.save_then(() => {
			window.open(
				frappe.urllib.get_full_url(
					"/printview?doctype=" +
						encodeURIComponent("HABC2 Examination Declaration") +
						"&name=" +
						encodeURIComponent(this.doc.name) +
						"&format=" +
						encodeURIComponent("HABC2 Examination Declaration") +
						"&no_letterhead=1"
				),
				"_blank"

			);
		});
	}

	init_signature_canvases() {
		this.$root.find(".h2-sign-canvas").each((_, canvas) => {
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
			const $wrap = $(canvas).closest(".h2-sign-wrap");
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

function h2Cint(value) {
	if (typeof window.cint === "function") {
		return window.cint(value);
	}
	const parsed = parseInt(value, 10);
	return Number.isNaN(parsed) ? 0 : parsed;
}
