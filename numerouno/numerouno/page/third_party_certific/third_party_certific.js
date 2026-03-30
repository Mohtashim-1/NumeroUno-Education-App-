frappe.pages["third-party-certific"].on_page_load = function (wrapper) {
	if (!wrapper.thirdPartyCertificatePage) {
		wrapper.thirdPartyCertificatePage = new ThirdPartyCertificatePage(wrapper);
	}
};

frappe.pages["third-party-certific"].refresh = function (wrapper) {
	wrapper.thirdPartyCertificatePage?.refresh();
};

class ThirdPartyCertificatePage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Third Party Certificate",
			single_column: true,
		});

		this.filter_controls = {};

		this.page.main.html(this.get_template());
		this.$summary = $(this.page.main).find('[data-region="summary"]');
		this.$body = $(this.page.main).find('[data-region="body"]');

		this.make_filters();
		this.refresh();
	}

	get_template() {
		return `
			<div class="card mb-3" style="background:#f8f9fa; border:1px solid #e2e6ea; border-radius:6px; padding:16px;">
				<div class="row">
					<div class="col-sm-3" data-filter="custom_company"></div>
					<div class="col-sm-3" data-filter="course"></div>
					<div class="col-sm-3" data-filter="student"></div>
					<div class="col-sm-3" data-filter="student_group"></div>
				</div>
				<div class="row mt-2">
					<div class="col-sm-3" data-filter="assessment_plan"></div>
					<div class="col-sm-3" data-filter="student_name"></div>
					<div class="col-sm-3" data-filter="grade"></div>
					<div class="col-sm-3 d-flex align-items-end" data-filter="pending_only"></div>
				</div>
				<div class="row mt-2">
					<div class="col-sm-3" data-filter="date_from"></div>
					<div class="col-sm-3" data-filter="date_to"></div>
					<div class="col-sm-6 d-flex align-items-end pb-1">
						<button class="btn btn-primary btn-sm apply-filters mr-2">${__("Apply Filters")}</button>
						<button class="btn btn-default btn-sm clear-filters">${__("Clear Filters")}</button>
					</div>
				</div>
			</div>
			<div class="mb-2 text-muted small" data-region="summary"></div>
			<div class="table-responsive">
				<table class="table table-bordered table-hover">
					<thead class="thead-light">
						<tr>
							<th>${__("Assessment Result")}</th>
							<th>${__("Student")}</th>
							<th>${__("Student Name")}</th>
							<th>${__("Course")}</th>
							<th>${__("Student Group")}</th>
							<th>${__("Assessment Plan")}</th>
							<th>${__("Company")}</th>
							<th>${__("Unique Certificate No")}</th>
							<th>${__("OPITO Learner No")}</th>
							<th>${__("Course Start Date")}</th>
							<th>${__("Grade")}</th>
							<th>${__("Certificate")}</th>
							<th>${__("Action")}</th>
						</tr>
					</thead>
					<tbody data-region="body">
						<tr><td colspan="13" class="text-center text-muted">${__("Loading...")}</td></tr>
					</tbody>
				</table>
			</div>
		`;
	}

	make_filters() {
		const filter_defs = [
			{ fieldname: "custom_company", label: __("Company"),        fieldtype: "Link",   options: "Company" },
			{ fieldname: "course",         label: __("Course"),         fieldtype: "Link",   options: "Course" },
			{ fieldname: "student",        label: __("Student"),        fieldtype: "Link",   options: "Student" },
			{ fieldname: "student_group",  label: __("Student Group"),  fieldtype: "Link",   options: "Student Group" },
			{ fieldname: "assessment_plan",label: __("Assessment Plan"),fieldtype: "Link",   options: "Assessment Plan" },
			{ fieldname: "student_name",   label: __("Student Name"),   fieldtype: "Data" },
			{ fieldname: "grade",          label: __("Grade"),          fieldtype: "Select", options: "\nPass\nFail" },
			{ fieldname: "pending_only",   label: __("Pending Only"),   fieldtype: "Check",  default: 1 },
			{ fieldname: "date_from",      label: __("From Date"),      fieldtype: "Date" },
			{ fieldname: "date_to",        label: __("To Date"),        fieldtype: "Date" },
		];

		filter_defs.forEach((df) => {
			const $container = $(this.page.main).find(`[data-filter="${df.fieldname}"]`);
			if (!$container.length) return;

			const ctrl = frappe.ui.form.make_control({
				parent: $container[0],
				df: { ...df, placeholder: df.label },
				render_input: true,
				only_input: false,
			});
			ctrl.refresh();

			if (df.default !== undefined) {
				ctrl.set_value(df.default);
			}

			this.filter_controls[df.fieldname] = ctrl;
		});

		$(this.page.main).find(".apply-filters").on("click", () => this.refresh());
		$(this.page.main).find(".clear-filters").on("click", () => this.clear_filters());
	}

	clear_filters() {
		Object.values(this.filter_controls).forEach((ctrl) => {
			ctrl.set_value(ctrl.df.fieldname === "pending_only" ? 1 : "");
		});
		this.refresh();
	}

	get_filters() {
		const get = (name) => {
			const ctrl = this.filter_controls[name];
			return ctrl ? ctrl.get_value() : null;
		};
		return {
			custom_company:  get("custom_company"),
			course:          get("course"),
			student:         get("student"),
			student_group:   get("student_group"),
			assessment_plan: get("assessment_plan"),
			student_name:    get("student_name"),
			grade:           get("grade"),
			pending_only:    get("pending_only") ? 1 : 0,
			date_from:       get("date_from"),
			date_to:         get("date_to"),
		};
	}

	refresh() {
		frappe.call({
			method: "numerouno.numerouno.api.third_party_certificate.get_assessment_results",
			args: { filters: this.get_filters() },
			freeze: true,
			freeze_message: __("Loading assessment results..."),
			callback: (r) => this.render_rows((r.message && r.message.rows) || []),
			error: () => {
				this.$summary.text(__("Failed to load data."));
				this.$body.html(`<tr><td colspan="13" class="text-center text-danger">${__("Failed to load data.")}</td></tr>`);
			},
		});
	}

	render_rows(rows) {
		this.$summary.text(__("{0} assessment result(s) found.", [rows.length]));

		if (!rows.length) {
			this.$body.html(`<tr><td colspan="13" class="text-center text-muted">${__("No records found.")}</td></tr>`);
			return;
		}

		const html = rows.map((row) => {
			const name             = escape_html(row.name);
			const student          = escape_html(row.student);
			const student_name     = escape_html(row.student_name);
			const course           = escape_html(row.course);
			const student_group    = escape_html(row.student_group);
			const assessment_plan  = escape_html(row.assessment_plan);
			const custom_company   = escape_html(row.custom_company);
			const unique_cert      = escape_html(row.custom_unique_certificate_no);
			const opito            = escape_html(row.custom_opito_learner_no);
			const course_start     = escape_html(row.course_start_date);
			const grade            = escape_html(row.grade);
			const grade_cell       = grade
				? `<span class="badge ${grade.toLowerCase() === "pass" ? "badge-success" : grade.toLowerCase() === "fail" ? "badge-danger" : "badge-secondary"}">${grade}</span>`
				: "-";
			const has_cert         = !!row.custom_certificate;
			const cert_cell        = has_cert
				? `<span class="badge badge-success">${__("Uploaded")}</span>&nbsp;<a href="${escape_html(row.custom_certificate)}" target="_blank"><i class="fa fa-eye"></i></a>`
				: `<span class="badge badge-warning">${__("Pending")}</span>`;

			return `
				<tr data-name="${name}">
					<td><a href="/app/assessment-result/${name}">${name}</a></td>
					<td>${student ? `<a href="/app/student/${student}">${student}</a>` : "-"}</td>
					<td>${student_name || "-"}</td>
					<td>${course || "-"}</td>
					<td>${student_group || "-"}</td>
					<td>${assessment_plan || "-"}</td>
					<td>${custom_company || "-"}</td>
					<td>${unique_cert || "-"}</td>
					<td>${opito || "-"}</td>
					<td>${course_start || "-"}</td>
					<td>${grade_cell}</td>
					<td class="certificate-status-cell">${cert_cell}</td>
					<td>
						<button class="btn btn-sm btn-default upload-certificate mr-1" data-name="${name}">
							<i class="fa fa-upload"></i> ${__("Upload")}
						</button>
						<button class="btn btn-sm btn-primary open-assessment-result" data-name="${name}">${__("Open")}</button>
					</td>
				</tr>
			`;
		}).join("");

		this.$body.html(html);

		const self = this;

		$(this.page.main).find(".open-assessment-result").off("click").on("click", function () {
			const name = $(this).data("name");
			if (name) frappe.set_route("Form", "Assessment Result", name);
		});

		$(this.page.main).find(".upload-certificate").off("click").on("click", function () {
			const name = $(this).data("name");
			if (!name) return;

			new frappe.ui.FileUploader({
				doctype: "Assessment Result",
				docname: name,
				fieldname: "custom_certificate",
				folder: "Home/Attachments",
				allow_multiple: false,
				restrictions: { allowed_file_types: ["image/*"] },
				on_success(file) {
					frappe.call({
						method: "numerouno.numerouno.api.third_party_certificate.update_certificate",
						args: { assessment_result: name, file_url: file.file_url },
						callback(r) {
							if (r.message && r.message.success) {
								frappe.show_alert({ message: __("Certificate uploaded successfully."), indicator: "green" });
								self.$body.find(`tr[data-name="${name}"]`).find(".certificate-status-cell").html(
									`<span class="badge badge-success">${__("Uploaded")}</span>&nbsp;<a href="${frappe.utils.escape_html(file.file_url)}" target="_blank"><i class="fa fa-eye"></i></a>`
								);
							}
						},
					});
				},
			});
		});
	}
}

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}
