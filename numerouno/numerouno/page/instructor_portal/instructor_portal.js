frappe.pages['instructor-portal'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Instructor Portal',
		single_column: true
	});

	var $body = $(`
		<style>
			@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Archivo:wght@400;600&display=swap");

			.instructor-portal {
				--ink: #0f1c2d;
				--muted: #5f6b7a;
				--surface: #ffffff;
				--surface-muted: #f3f6f9;
				--accent: #ff7a3d;
				--accent-dark: #d85c24;
				--teal: #1a7f7a;
				font-family: "Archivo", "Space Grotesk", sans-serif;
				color: var(--ink);
				background:
					radial-gradient(1200px 500px at -10% -10%, #ffe9dd 0%, rgba(255, 233, 221, 0) 65%),
					radial-gradient(1000px 400px at 110% 0%, #d7f4f3 0%, rgba(215, 244, 243, 0) 60%),
					linear-gradient(180deg, #f5f4ef 0%, #eef2f6 60%, #f9fafb 100%);
				border-radius: 18px;
				padding: 28px;
				margin-top: 12px;
			}

			.instructor-hero {
				display: flex;
				flex-wrap: wrap;
				gap: 18px;
				justify-content: space-between;
				align-items: center;
				margin-bottom: 24px;
			}

			.instructor-hero h2 {
				font-family: "Space Grotesk", "Archivo", sans-serif;
				font-size: 28px;
				font-weight: 700;
				letter-spacing: -0.02em;
				margin: 0;
			}

			.instructor-hero p {
				margin: 6px 0 0;
				color: var(--muted);
				font-size: 14px;
			}

			.portal-metrics {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
				gap: 14px;
				flex: 1;
			}

			.metric-card {
				background: var(--surface);
				border-radius: 14px;
				padding: 14px 16px;
				box-shadow: 0 12px 28px rgba(15, 28, 45, 0.08);
			}

			.metric-card h5 {
				font-size: 12px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: var(--muted);
				margin: 0 0 8px;
			}

			.metric-card .value {
				font-family: "Space Grotesk", "Archivo", sans-serif;
				font-size: 22px;
				font-weight: 700;
				color: var(--ink);
			}

			.portal-grid {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
				gap: 20px;
			}

			.portal-tabs {
				display: flex;
				gap: 10px;
				margin: 10px 0 18px;
				flex-wrap: wrap;
			}

			.portal-tab {
				border: 1px solid #e3e6ea;
				background: #ffffff;
				color: var(--ink);
				border-radius: 999px;
				padding: 8px 16px;
				font-size: 13px;
				font-weight: 600;
				cursor: pointer;
			}

			.portal-tab.active {
				background: var(--accent);
				border-color: var(--accent);
				color: #ffffff;
			}

			.portal-section[hidden] {
				display: none;
			}

			.portal-panel {
				background: var(--surface);
				border-radius: 18px;
				box-shadow: 0 12px 30px rgba(15, 28, 45, 0.08);
				padding: 18px;
				display: flex;
				flex-direction: column;
				gap: 12px;
			}

			.panel-header {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 12px;
			}

			.panel-title {
				display: flex;
				align-items: center;
				gap: 12px;
			}

			.panel-title span {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 40px;
				height: 40px;
				border-radius: 12px;
				background: var(--surface-muted);
				color: var(--accent-dark);
				font-weight: 700;
				font-size: 16px;
			}

			.panel-title h3 {
				margin: 0;
				font-size: 18px;
				font-family: "Space Grotesk", "Archivo", sans-serif;
			}

			.panel-subtitle {
				margin: 4px 0 0;
				font-size: 13px;
				color: var(--muted);
			}

			.table {
				margin-bottom: 0;
				border-collapse: separate;
				border-spacing: 0 10px;
			}

			.table thead th {
				border: none;
				color: var(--muted);
				font-size: 12px;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				padding: 0 12px 6px;
			}

			.table tbody tr {
				background: var(--surface-muted);
				box-shadow: 0 6px 20px rgba(15, 28, 45, 0.06);
				transition: transform 0.15s ease, box-shadow 0.15s ease;
			}

			.table tbody td {
				border: none;
				padding: 12px;
				vertical-align: middle;
			}

			.table tbody tr:hover {
				transform: translateY(-2px);
				box-shadow: 0 10px 24px rgba(15, 28, 45, 0.12);
			}

			.data-meta {
				font-size: 11px;
				color: var(--muted);
				margin-top: 4px;
			}

			.data-title {
				font-weight: 600;
			}

			.signature-inline {
				display: inline-flex;
				align-items: center;
				gap: 8px;
				color: var(--muted);
				font-size: 12px;
			}

			.table tbody tr td:first-child {
				border-radius: 12px 0 0 12px;
			}

			.table tbody tr td:last-child {
				border-radius: 0 12px 12px 0;
			}

			.signature-canvas {
				width: 160px;
				height: 64px;
				border: 1px dashed #d5a28a;
				border-radius: 10px;
				background: #fffdfb;
				display: block;
			}

			.portal-btn {
				border: none;
				border-radius: 8px;
				padding: 6px 12px;
				font-size: 12px;
				font-weight: 600;
				cursor: pointer;
			}

			.portal-btn-primary {
				background: var(--accent);
				color: #ffffff;
			}

			.portal-btn-ghost {
				background: #f2f3f5;
				color: var(--ink);
			}

			.status-pill {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				border-radius: 999px;
				padding: 4px 10px;
				font-size: 12px;
				font-weight: 600;
				background: #e9f6f5;
				color: var(--teal);
			}

			.status-pill.absent {
				background: #ffe8e3;
				color: #b43c1b;
			}

			.signature {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				width: 140px;
				height: 60px;
				background: #fff7f2;
				border-radius: 10px;
				border: 1px dashed #f4c1a5;
				overflow: hidden;
			}

			.signature img {
				max-width: 100%;
				max-height: 100%;
				object-fit: contain;
			}

			.empty-state {
				text-align: center;
				color: var(--muted);
				padding: 18px 0;
			}

			@media (max-width: 768px) {
				.instructor-portal {
					padding: 18px;
				}

				.instructor-hero {
					flex-direction: column;
					align-items: flex-start;
				}
			}
		</style>

		<div class="instructor-portal">
			<div class="instructor-hero">
				<div>
					<h2>Welcome back, Instructor</h2>
					<p>Quick view of attendance and student card activity for your assigned groups.</p>
				</div>
				<div class="portal-metrics">
					<div class="metric-card">
						<h5>Total Attendance</h5>
						<div class="value" id="metric-attendance">0</div>
					</div>
					<div class="metric-card">
						<h5>Present Records</h5>
						<div class="value" id="metric-present">0</div>
					</div>
					<div class="metric-card">
						<h5>Student Cards</h5>
						<div class="value" id="metric-cards">0</div>
					</div>
				</div>
			</div>

			<div class="portal-grid">
				<div class="portal-tabs">
					<button type="button" class="portal-tab active" data-target="attendance-section">Attendance</button>
					<button type="button" class="portal-tab" data-target="cards-section">Student Cards</button>
				</div>
			</div>

			<div class="portal-section" id="attendance-section">
				<div class="portal-panel">
					<div class="panel-header">
						<div class="panel-title">
							<span>AT</span>
							<div>
								<h3>Student Attendance</h3>
								<p class="panel-subtitle">Attendance records ordered by date (newest to oldest).</p>
							</div>
						</div>
					</div>
					<div class="table-responsive">
						<table class="table">
							<thead>
								<tr>
									<th>Attendance</th>
									<th>Group</th>
									<th>Student</th>
									<th>Date</th>
									<th>Status</th>
									<th>Signature</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody id="instructor-attendance-body">
								<tr>
									<td colspan="7" class="empty-state">Loading...</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>

			<div class="portal-section" id="cards-section" hidden>
				<div class="portal-panel">
					<div class="panel-header">
						<div class="panel-title">
							<span>SC</span>
							<div>
								<h3>Student Cards</h3>
								<p class="panel-subtitle">Cards and signatures for your assigned students.</p>
							</div>
						</div>
					</div>
					<div class="table-responsive">
						<table class="table">
							<thead>
								<tr>
									<th>Card</th>
									<th>Group</th>
									<th>Student</th>
									<th>Signature</th>
									<th>Action</th>
								</tr>
							</thead>
							<tbody id="instructor-cards-body">
								<tr>
									<td colspan="5" class="empty-state">Loading...</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	`).appendTo(page.body);

	var attendanceOffset = 0;
	var cardsOffset = 0;
	var pageSize = 50;

	load_portal_data();
	init_tabs();

	function load_portal_data() {
		frappe.call({
			method: "numerouno.numerouno.page.instructor_portal.instructor_portal.get_instructor_portal_data",
			args: {
				attendance_limit: pageSize,
				attendance_offset: attendanceOffset,
				card_limit: pageSize,
				card_offset: cardsOffset
			},
			callback: function (r) {
				var message = r.message || {};
				render_attendance(message.attendance || [], attendanceOffset > 0);
				render_cards(message.cards || [], cardsOffset > 0);
				if (attendanceOffset === 0 && cardsOffset === 0) {
					render_metrics(
						message.attendance || [],
						message.cards || [],
						message.attendance_total,
						message.present_total,
						message.cards_total
					);
				}
			},
			error: function () {
				render_attendance([]);
				render_cards([]);
				render_metrics([], []);
				frappe.msgprint("Unable to load instructor data.");
			}
		});
	}

	function init_tabs() {
		$('.portal-tab').off('click').on('click', function () {
			var target = $(this).data('target');
			$('.portal-tab').removeClass('active');
			$(this).addClass('active');
			$('.portal-section').attr('hidden', true);
			$(`#${target}`).removeAttr('hidden');
		});
	}

	function render_attendance(records, append) {
		var $body = $("#instructor-attendance-body");
		if (!append) {
			$body.empty();
			records = records.slice().sort(function (a, b) {
				var dateA = a.date ? new Date(a.date) : new Date(0);
				var dateB = b.date ? new Date(b.date) : new Date(0);
				return dateB - dateA;
			});
		}

		if (!records.length) {
			if (!append) {
				$body.append(`
					<tr>
						<td colspan="7" class="empty-state">No attendance records found.</td>
					</tr>
				`);
			}
			return;
		}

		records.forEach(function (row) {
			var attendanceLink = row.name
				? `<a href="/app/student-attendance/${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(row.name)}</a>`
				: "";
			var studentLink = row.student
				? `<a href="/app/student/${frappe.utils.escape_html(row.student)}">${frappe.utils.escape_html(row.student)}</a>`
				: "";
			var groupLink = row.student_group
				? `<a href="/app/student-group/${frappe.utils.escape_html(row.student_group)}">${frappe.utils.escape_html(row.student_group)}</a>`
				: "";
			var dateLabel = row.date ? frappe.datetime.str_to_user(row.date) : "";
			var statusLabel = row.status || "";
			var statusClass = statusLabel === "Absent" ? "absent" : "";
			var signatureCell = "";
			var actionCell = "";

			if (row.custom_student_signature) {
				signatureCell = `<span class="signature"><img src="${row.custom_student_signature}" alt="Signature"></span>`;
				if (row.docstatus === 0) {
					actionCell = `
						<button class="portal-btn portal-btn-primary att-submit-btn" data-name="${row.name}">Submit</button>
					`;
				} else {
					actionCell = `<span class="text-muted">Submitted</span>`;
				}
			} else if (row.docstatus === 0) {
				signatureCell = `
					<canvas class="signature-canvas" id="att-sign-${row.name}" width="160" height="64"></canvas>
				`;
				actionCell = `
					<div class="d-flex gap-2">
						<button class="portal-btn portal-btn-ghost att-clear-btn" data-name="${row.name}">Clear</button>
						<button class="portal-btn portal-btn-primary att-sign-btn" data-name="${row.name}">Sign & Submit</button>
					</div>
				`;
			} else {
				signatureCell = `<span class="text-muted">No signature</span>`;
				actionCell = `<span class="text-muted">Submitted</span>`;
			}

			$body.append(`
				<tr>
					<td>
						<div class="data-title">${attendanceLink}</div>
						<div class="data-meta">${row.docstatus === 1 ? "Submitted" : "Draft"}</div>
					</td>
					<td>
						<div class="data-title">${groupLink}</div>
					</td>
					<td>
						<div class="data-title">${studentLink}</div>
						<div class="data-meta">${frappe.utils.escape_html(row.student_name || "")}</div>
					</td>
					<td>
						<div class="data-title">${frappe.utils.escape_html(dateLabel || "")}</div>
					</td>
					<td><span class="status-pill ${statusClass}">${frappe.utils.escape_html(statusLabel || "-")}</span></td>
					<td>${signatureCell || `<span class="signature-inline">No signature</span>`}</td>
					<td>${actionCell}</td>
				</tr>
			`);
		});

		init_signature_canvases('att-sign-');
		bind_attendance_actions();
		bind_attendance_load_more(records.length);
	}

	function render_cards(records, append) {
		var $body = $("#instructor-cards-body");
		if (!append) {
			$body.empty();
			records = records.slice().sort(function (a, b) {
				var nameA = (a.student_name || a.student || "").toLowerCase();
				var nameB = (b.student_name || b.student || "").toLowerCase();
				return nameA.localeCompare(nameB);
			});
		}

		if (!records.length) {
			if (!append) {
				$body.append(`
					<tr>
						<td colspan="5" class="empty-state">No student cards found.</td>
					</tr>
				`);
			}
			return;
		}

		records.forEach(function (row) {
			var cardLink = row.name
				? `<a href="/app/student-card/${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(row.name)}</a>`
				: "";
			var studentLink = row.student
				? `<a href="/app/student/${frappe.utils.escape_html(row.student)}">${frappe.utils.escape_html(row.student)}</a>`
				: "";
			var groupLink = row.student_group
				? `<a href="/app/student-group/${frappe.utils.escape_html(row.student_group)}">${frappe.utils.escape_html(row.student_group)}</a>`
				: "";

			var signatureHtml = "";
			var actionCell = "";

			if (row.student_signature) {
				signatureHtml = `<span class="signature"><img src="${row.student_signature}" alt="Signature"></span>`;
				if (row.docstatus === 0) {
					actionCell = `
						<button class="portal-btn portal-btn-primary card-submit-btn" data-name="${row.name}">Submit</button>
					`;
				} else {
					actionCell = `<span class="text-muted">Submitted</span>`;
				}
			} else if (row.docstatus === 0) {
				signatureHtml = `
					<canvas class="signature-canvas" id="card-sign-${row.name}" width="160" height="64"></canvas>
				`;
				actionCell = `
					<div class="d-flex gap-2">
						<button class="portal-btn portal-btn-ghost card-clear-btn" data-name="${row.name}">Clear</button>
						<button class="portal-btn portal-btn-primary card-sign-btn" data-name="${row.name}">Sign & Submit</button>
					</div>
				`;
			} else {
				signatureHtml = `<span class="text-muted">No signature</span>`;
				actionCell = `<span class="text-muted">Submitted</span>`;
			}

			$body.append(`
				<tr>
					<td>
						<div class="data-title">${cardLink}</div>
						<div class="data-meta">${row.docstatus === 1 ? "Submitted" : "Draft"}</div>
					</td>
					<td>
						<div class="data-title">${groupLink}</div>
					</td>
					<td>
						<div class="data-title">${studentLink}</div>
						<div class="data-meta">${frappe.utils.escape_html(row.student_name || "")}</div>
					</td>
					<td>${signatureHtml}</td>
					<td>${actionCell}</td>
				</tr>
			`);
		});

		init_signature_canvases('card-sign-');
		bind_card_actions();
		bind_cards_load_more(records.length);
	}

	function render_metrics(attendance, cards, attendanceTotal, presentTotal, cardsTotal) {
		var presentCount = attendance.filter(function (row) {
			return row.status === "Present";
		}).length;

		$("#metric-attendance").text(attendanceTotal || attendance.length);
		$("#metric-present").text(presentTotal || presentCount);
		$("#metric-cards").text(cardsTotal || cards.length);
	}

	function bind_attendance_load_more(count) {
		$("#attendance-load-more").remove();
		if (count < pageSize) return;

		$("#attendance-section .portal-panel").append(`
			<div class="mt-2 text-center">
				<button type="button" class="portal-btn portal-btn-ghost" id="attendance-load-more">Load more</button>
			</div>
		`);

		$("#attendance-load-more").off('click').on('click', function () {
			attendanceOffset += pageSize;
			load_portal_data();
		});
	}

	function bind_cards_load_more(count) {
		$("#cards-load-more").remove();
		if (count < pageSize) return;

		$("#cards-section .portal-panel").append(`
			<div class="mt-2 text-center">
				<button type="button" class="portal-btn portal-btn-ghost" id="cards-load-more">Load more</button>
			</div>
		`);

		$("#cards-load-more").off('click').on('click', function () {
			cardsOffset += pageSize;
			load_portal_data();
		});
	}

	function init_signature_canvases(prefix) {
		$(`canvas[id^="${prefix}"]`).each(function () {
			var canvas = this;
			var ctx = canvas.getContext('2d');
			var drawing = false;

			canvas.addEventListener('mousedown', function (e) {
				drawing = true;
				ctx.beginPath();
				ctx.moveTo(e.offsetX, e.offsetY);
			});
			canvas.addEventListener('mousemove', function (e) {
				if (drawing) {
					ctx.lineTo(e.offsetX, e.offsetY);
					ctx.stroke();
				}
			});
			canvas.addEventListener('mouseup', function () {
				drawing = false;
			});
			canvas.addEventListener('mouseleave', function () {
				drawing = false;
			});
		});
	}

	function is_canvas_blank(canvas) {
		var ctx = canvas.getContext('2d');
		var pixelBuffer = new Uint32Array(
			ctx.getImageData(0, 0, canvas.width, canvas.height).data.buffer
		);
		return !pixelBuffer.some(function (color) {
			return color !== 0;
		});
	}

	function submit_doc(doctype, name, done) {
		frappe.call({
			method: "frappe.client.get",
			args: { doctype: doctype, name: name },
			callback: function (res) {
				frappe.call({
					method: "frappe.client.submit",
					args: { doc: res.message },
					callback: function () {
						if (done) done();
					},
					error: function () {
						frappe.msgprint("Failed to submit the document. Please try again.");
					}
				});
			}
		});
	}

	function bind_attendance_actions() {
		$('.att-clear-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			var canvas = document.getElementById(`att-sign-${name}`);
			if (!canvas) return;
			var ctx = canvas.getContext('2d');
			ctx.clearRect(0, 0, canvas.width, canvas.height);
		});

		$('.att-sign-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			var canvas = document.getElementById(`att-sign-${name}`);
			if (!canvas) return frappe.msgprint("Signature area not found.");

			if (is_canvas_blank(canvas)) {
				frappe.msgprint("Please draw the signature before submitting.");
				return;
			}

			var signature = canvas.toDataURL();
			frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Student Attendance",
					name: name,
					fieldname: { "custom_student_signature": signature }
				},
				callback: function () {
					submit_doc("Student Attendance", name, load_portal_data);
				}
			});
		});

		$('.att-submit-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			submit_doc("Student Attendance", name, load_portal_data);
		});
	}

	function bind_card_actions() {
		$('.card-clear-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			var canvas = document.getElementById(`card-sign-${name}`);
			if (!canvas) return;
			var ctx = canvas.getContext('2d');
			ctx.clearRect(0, 0, canvas.width, canvas.height);
		});

		$('.card-sign-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			var canvas = document.getElementById(`card-sign-${name}`);
			if (!canvas) return frappe.msgprint("Signature area not found.");

			if (is_canvas_blank(canvas)) {
				frappe.msgprint("Please draw the signature before submitting.");
				return;
			}

			var signature = canvas.toDataURL();
			frappe.call({
				method: "frappe.client.set_value",
				args: {
					doctype: "Student Card",
					name: name,
					fieldname: { "student_signature": signature }
				},
				callback: function () {
					submit_doc("Student Card", name, load_portal_data);
				}
			});
		});

		$('.card-submit-btn').off('click').on('click', function () {
			var name = $(this).data('name');
			submit_doc("Student Card", name, load_portal_data);
		});
	}
}
