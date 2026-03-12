frappe.pages["assesment-result-cre"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Assesment Result Creation Failed Report",
		single_column: true,
	});

	const state = {
		records: [],
	};
	page.arc_state = state;
	page.arc_load = () => load_data(state, page);

	page.set_primary_action("Create Selected", () => create_selected(state, page));
	page.add_inner_button("Create All Filtered", () => create_all_filtered(state, page));
	page.set_secondary_action("Refresh", () => load_data(state, page));

	$(page.body).html(`
		<div class="mb-3">
			<p class="text-muted mb-2">
				Quiz Activities where Assessment Result is missing. Use bulk action to retry creation.
			</p>
			<div id="assessment-result-cre-summary" class="small text-muted"></div>
		</div>
		<div class="table-responsive">
			<table class="table table-bordered table-hover">
				<thead>
					<tr>
						<th style="width:38px;">
							<input type="checkbox" id="arc-select-all" />
						</th>
						<th>Quiz Activity</th>
						<th>Student</th>
						<th>Student Group</th>
						<th>Quiz</th>
						<th>Score</th>
						<th>Status</th>
						<th>Date</th>
						<th>Reason</th>
						<th style="width:110px;">Action</th>
					</tr>
				</thead>
				<tbody id="assessment-result-cre-body">
					<tr><td colspan="10" class="text-muted text-center">Loading...</td></tr>
				</tbody>
			</table>
		</div>
	`);

	$(page.body).on("change", "#arc-select-all", function () {
		const checked = !!$(this).prop("checked");
		$(page.body).find(".arc-row-check").prop("checked", checked);
	});

	$(page.body).on("click", ".arc-create-one", function () {
		const name = $(this).data("name");
		if (!name) return;
		create_bulk(page, [name]);
	});

	page.arc_load();
};

function escape_html(value) {
	return frappe.utils.escape_html(value == null ? "" : String(value));
}

function load_data(state, page) {
	frappe.call({
		method: "numerouno.numerouno.page.assesment_result_cre.assesment_result_cre.get_failed_quiz_activities",
		args: { limit: 500 },
		freeze: true,
		freeze_message: "Loading quiz activities...",
		callback: (r) => {
			state.records = (r.message && r.message.records) || [];
			render_rows(state, page);
		},
		error: () => {
			state.records = [];
			render_rows(state, page);
			frappe.msgprint("Failed to load quiz activities.");
		},
	});
}

function render_rows(state, page) {
	const $body = $(page.body).find("#assessment-result-cre-body");
	const $summary = $(page.body).find("#assessment-result-cre-summary");
	const rows = state.records || [];
	$summary.text(`Total pending quiz activities: ${rows.length}`);

	if (!rows.length) {
		$body.html('<tr><td colspan="10" class="text-center text-muted">No pending records found.</td></tr>');
		return;
	}

	const html = rows
		.map((row) => {
			const qa = escape_html(row.quiz_activity);
			const student = escape_html(row.student);
			const studentGroup = escape_html(row.student_group);
			const quiz = escape_html(row.quiz);
			const score = escape_html(row.score);
			const status = escape_html(row.status);
			const date = row.activity_date ? escape_html(frappe.datetime.str_to_user(row.activity_date)) : "-";
			const reason = escape_html(row.reason);
			return `
				<tr>
					<td><input type="checkbox" class="arc-row-check" data-name="${qa}" /></td>
					<td><a href="/app/quiz-activity/${qa}" target="_blank">${qa}</a></td>
					<td><a href="/app/student/${student}" target="_blank">${student}</a></td>
					<td>${studentGroup ? `<a href="/app/student-group/${studentGroup}" target="_blank">${studentGroup}</a>` : "-"}</td>
					<td>${quiz ? `<a href="/app/quiz/${quiz}" target="_blank">${quiz}</a>` : "-"}</td>
					<td>${score || "-"}</td>
					<td>${status || "-"}</td>
					<td>${date}</td>
					<td style="max-width:420px; white-space:normal;">${reason}</td>
					<td><button class="btn btn-xs btn-primary arc-create-one" data-name="${qa}">Create</button></td>
				</tr>
			`;
		})
		.join("");

	$body.html(html);
}

function get_selected_names(page) {
	const names = [];
	$(page.body)
		.find(".arc-row-check:checked")
		.each(function () {
			const n = $(this).data("name");
			if (n) names.push(n);
		});
	return names;
}

function create_selected(state, page) {
	const names = get_selected_names(page);
	if (!names.length) {
		frappe.msgprint("Please select at least one Quiz Activity.");
		return;
	}
	create_bulk(page, names);
}

function create_all_filtered(state, page) {
	const names = (state.records || []).map((d) => d.quiz_activity).filter(Boolean);
	if (!names.length) {
		frappe.msgprint("No records available.");
		return;
	}
	frappe.confirm(
		`Create Assessment Results for all ${names.length} filtered records?`,
		() => create_bulk(page, names)
	);
}

function create_bulk(page, names) {
	frappe.call({
		method: "numerouno.numerouno.page.assesment_result_cre.assesment_result_cre.create_assessment_results_bulk",
		args: { quiz_activity_names: names },
		freeze: true,
		freeze_message: `Creating Assessment Results for ${names.length} record(s)...`,
		callback: (r) => {
			const msg = r.message || {};
			const created = msg.created_count || 0;
			const existing = msg.existing_count || 0;
			const failed = msg.failed_count || 0;

			let details = `Created: ${created}<br>Already Existing: ${existing}<br>Failed: ${failed}`;
			if (failed > 0 && Array.isArray(msg.failed)) {
				const topFailed = msg.failed
					.slice(0, 10)
					.map((f) => `<li>${escape_html(f.quiz_activity)}: ${escape_html(f.reason)}</li>`)
					.join("");
				if (topFailed) details += `<br><br><b>Failed Reasons (top 10):</b><ul>${topFailed}</ul>`;
			}

			frappe.msgprint({
				title: "Bulk Create Result",
				indicator: failed ? "orange" : "green",
				message: details,
			});

			const activePage = frappe.container && frappe.container.page ? frappe.container.page.page : null;
			if (activePage && activePage.arc_load) {
				activePage.arc_load();
			} else {
				location.reload();
			}
		},
		error: () => {
			frappe.msgprint("Bulk creation failed.");
		},
	});
}
