import frappe


PAGE_SCRIPT = r"""
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

		this.filters = {};
		this.make_filters();
		this.page.set_primary_action(__("Refresh"), () => this.refresh());

		this.page.main.html(this.get_template());
		this.$summary = $(this.page.main).find('[data-region="summary"]');
		this.$body = $(this.page.main).find('[data-region="body"]');

		this.refresh();
	}

	make_filters() {
		this.filters.custom_company = this.page.add_field({
			label: __("Company"),
			fieldname: "custom_company",
			fieldtype: "Link",
			options: "Company",
			change: () => this.refresh(),
		});

		this.filters.course = this.page.add_field({
			label: __("Course"),
			fieldname: "course",
			fieldtype: "Link",
			options: "Course",
			change: () => this.refresh(),
		});

		this.filters.student = this.page.add_field({
			label: __("Student"),
			fieldname: "student",
			fieldtype: "Link",
			options: "Student",
			change: () => this.refresh(),
		});

		this.filters.student_group = this.page.add_field({
			label: __("Student Group"),
			fieldname: "student_group",
			fieldtype: "Link",
			options: "Student Group",
			change: () => this.refresh(),
		});

		this.filters.assessment_plan = this.page.add_field({
			label: __("Assessment Plan"),
			fieldname: "assessment_plan",
			fieldtype: "Link",
			options: "Assessment Plan",
			change: () => this.refresh(),
		});

		this.filters.student_name = this.page.add_field({
			label: __("Student Name"),
			fieldname: "student_name",
			fieldtype: "Data",
			change: () => this.refresh(),
		});

		this.filters.pending_only = this.page.add_field({
			label: __("Pending Only"),
			fieldname: "pending_only",
			fieldtype: "Check",
			default: 1,
			change: () => this.refresh(),
		});
	}

	get_template() {
		return `
			<div class="mb-3 text-muted" data-region="summary">Loading...</div>
			<div class="table-responsive">
				<table class="table table-bordered table-hover">
					<thead>
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
							<th>${__("Certificate")}</th>
							<th>${__("Action")}</th>
						</tr>
					</thead>
					<tbody data-region="body">
						<tr><td colspan="11" class="text-center text-muted">${__("Loading...")}</td></tr>
					</tbody>
				</table>
			</div>
		`;
	}

	get_filters() {
		return {
			custom_company: this.filters.custom_company.get_value(),
			course: this.filters.course.get_value(),
			student: this.filters.student.get_value(),
			student_group: this.filters.student_group.get_value(),
			assessment_plan: this.filters.assessment_plan.get_value(),
			student_name: this.filters.student_name.get_value(),
			pending_only: this.filters.pending_only.get_value() ? 1 : 0,
		};
	}

	refresh() {
		frappe.call({
			method: "numerouno.numerouno.api.third_party_certificate.get_assessment_results",
			args: {
				filters: this.get_filters(),
			},
			freeze: true,
			freeze_message: __("Loading assessment results..."),
			callback: (r) => this.render_rows((r.message && r.message.rows) || []),
			error: () => {
				this.$summary.text(__("Failed to load data."));
				this.$body.html(`<tr><td colspan="11" class="text-center text-danger">${__("Failed to load data.")}</td></tr>`);
			},
		});
	}

	render_rows(rows) {
		this.$summary.text(__("{0} assessment result(s) found.", [rows.length]));

		if (!rows.length) {
			this.$body.html(`<tr><td colspan="11" class="text-center text-muted">${__("No records found.")}</td></tr>`);
			return;
		}

		const html = rows.map((row) => {
			const name = escape_html(row.name);
			const student = escape_html(row.student);
			const student_name = escape_html(row.student_name);
			const course = escape_html(row.course);
			const student_group = escape_html(row.student_group);
			const assessment_plan = escape_html(row.assessment_plan);
			const custom_company = escape_html(row.custom_company);
			const unique_certificate = escape_html(row.custom_unique_certificate_no);
			const opito = escape_html(row.custom_opito_learner_no);
			const has_certificate = !!row.custom_certificate;
			const certificate_cell = has_certificate
				? `<span class="badge badge-success">${__("Uploaded")}</span>&nbsp;<a href="${escape_html(row.custom_certificate)}" target="_blank" title="${__("View Certificate")}"><i class="fa fa-eye"></i></a>`
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
					<td>${unique_certificate || "-"}</td>
					<td>${opito || "-"}</td>
					<td class="certificate-status-cell">${certificate_cell}</td>
					<td>
						<button class="btn btn-sm btn-default upload-certificate mr-1" data-name="${name}" title="${__("Upload Certificate Image")}">
							<i class="fa fa-upload"></i> ${__("Upload")}
						</button>
						<button class="btn btn-sm btn-primary open-assessment-result" data-name="${name}">${__("Open")}</button>
					</td>
				</tr>
			`;
		}).join("");

		this.$body.html(html);

		const self = this;

		$(this.page.main)
			.find(".open-assessment-result")
			.off("click")
			.on("click", function () {
				const name = $(this).data("name");
				if (name) {
					frappe.set_route("Form", "Assessment Result", name);
				}
			});

		$(this.page.main)
			.find(".upload-certificate")
			.off("click")
			.on("click", function () {
				const name = $(this).data("name");
				if (!name) return;

				new frappe.ui.FileUploader({
					doctype: "Assessment Result",
					docname: name,
					fieldname: "custom_certificate",
					folder: "Home/Attachments",
					allow_multiple: false,
					restrictions: {
						allowed_file_types: ["image/*"],
					},
					on_success(file) {
						frappe.call({
							method: "numerouno.numerouno.api.third_party_certificate.update_certificate",
							args: {
								assessment_result: name,
								file_url: file.file_url,
							},
							callback(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: __("Certificate uploaded successfully."),
										indicator: "green",
									});
									const $row = self.$body.find(`tr[data-name="${name}"]`);
									$row.find(".certificate-status-cell").html(
										`<span class="badge badge-success">${__("Uploaded")}</span>&nbsp;<a href="${frappe.utils.escape_html(file.file_url)}" target="_blank" title="${__("View Certificate")}"><i class="fa fa-eye"></i></a>`
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
"""


@frappe.whitelist()
def get_assessment_results(filters=None):
	filters = frappe.parse_json(filters) or {}

	assessment_filters = {}

	if filters.get("pending_only", 1):
		assessment_filters["custom_certificate"] = ["is", "not set"]

	for fieldname in ("custom_company", "course", "student", "student_group", "assessment_plan"):
		value = filters.get(fieldname)
		if value:
			assessment_filters[fieldname] = value

	student_name = filters.get("student_name")
	if student_name:
		assessment_filters["student_name"] = ["like", f"%{student_name}%"]

	date_from = filters.get("date_from")
	date_to = filters.get("date_to")
	if date_from and date_to:
		assessment_filters["course_start_date"] = ["between", [date_from, date_to]]
	elif date_from:
		assessment_filters["course_start_date"] = [">=", date_from]
	elif date_to:
		assessment_filters["course_start_date"] = ["<=", date_to]

	grade = filters.get("grade")
	if grade:
		assessment_filters["grade"] = grade

	rows = frappe.get_all(
		"Assessment Result",
		filters=assessment_filters,
		fields=[
			"name",
			"student",
			"student_name",
			"course",
			"student_group",
			"assessment_plan",
			"custom_company",
			"custom_unique_certificate_no",
			"custom_opito_learner_no",
			"custom_certificate",
			"course_start_date",
			"grade",
			"modified",
		],
		order_by="modified desc",
		limit_page_length=500,
	)

	return {"rows": rows}


@frappe.whitelist()
def update_certificate(assessment_result, file_url):
	doc = frappe.get_doc("Assessment Result", assessment_result)
	doc.custom_certificate = file_url
	doc.save(ignore_permissions=False)
	return {"success": True}


@frappe.whitelist()
def install_page_script():
	frappe.db.set_value("Page", "third-party-certific", "script", PAGE_SCRIPT, update_modified=False)
	frappe.clear_cache()
	return {"updated": True}
