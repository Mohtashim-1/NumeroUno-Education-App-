frappe.pages["car-dashboard"].on_page_load = function (wrapper) {
	new CarDashboard(wrapper);
};

class CarDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Car Dashboard",
			single_column: true,
		});

		this.page.set_primary_action(__("New Car Entry"), () => {
			frappe.new_doc("Car Entry");
		});

		this.page.set_secondary_action(__("View Car Entry List"), () => {
			frappe.set_route("List", "Car Entry");
		});

		this.render();
		this.init_controls();
		this.bind_events();
		this.load_dashboard();
	}

	render() {
		this.wrapper.find(".layout-main-section").html(`
			<div class="car-dashboard">
				<div class="car-dashboard-shell">
					<div class="car-dashboard-header">
						<h1>Vehicle Movement Logs</h1>
						<p>Entry, exit, and odometer tracking in one place.</p>
					</div>
					
					<div class="car-dashboard-grid">
						<div class="car-panel car-panel-entry">
							<div class="car-panel-title">Car Entry</div>
							<div class="car-field" id="entry-vehicle-control"></div>
							<div class="car-field" id="entry-driver-control"></div>
							<div class="car-field">
								<label>Odometer In</label>
								<input type="number" min="0" class="form-control" id="car-entry-odometer" placeholder="Odometer In">
							</div>
							<div class="car-field" id="entry-dashboard-image-control"></div>
							<div class="car-field" id="entry-condition-image-control"></div>
							<button class="btn btn-primary car-submit" id="submit-car-entry">Submit Entry</button>
						</div>
						<div class="car-panel car-panel-exit">
							<div class="car-panel-title">Car Exit</div>
							<div class="car-field">
								<label>Select Active Car</label>
								<select class="form-control" id="car-exit-record">
									<option value="">Select Active Car</option>
								</select>
							</div>
							<div class="car-active-meta" id="car-active-meta">Choose an active car to see the entry odometer.</div>
							<div class="car-field">
								<label>Odometer Out</label>
								<input type="number" min="0" class="form-control" id="car-exit-odometer" placeholder="Odometer Out">
							</div>
							<div class="car-field" id="exit-dashboard-image-control"></div>
							<div class="car-field" id="exit-condition-image-control"></div>
							<button class="btn btn-warning car-submit" id="submit-car-exit">Submit Exit</button>
						</div>
					</div>
					<div class="car-log-panel">
						<div class="car-log-title">Vehicle Movement Logs</div>
						<div id="car-log-table"></div>
					</div>
				</div>
			</div>
		`);

		this.inject_styles();
	}

	init_controls() {
		this.entry_vehicle_control = frappe.ui.form.make_control({
			parent: this.wrapper.find("#entry-vehicle-control"),
			df: {
				fieldname: "vehicle",
				fieldtype: "Link",
				label: "Select Car",
				options: "Vehicle",
				reqd: 1,
				placeholder: "Select Car",
			},
			render_input: true,
		});

		this.entry_driver_control = frappe.ui.form.make_control({
			parent: this.wrapper.find("#entry-driver-control"),
			df: {
				fieldname: "driver_name",
				fieldtype: "Link",
				label: "Driver Name",
				options: "User",
				reqd: 1,
				placeholder: "Select Driver",
			},
			render_input: true,
		});

		this.entry_dashboard_image_control = this.make_attach_control("#entry-dashboard-image-control", "Dashboard Image");
		this.entry_condition_image_control = this.make_attach_control("#entry-condition-image-control", "Vehicle Condition");
		this.exit_dashboard_image_control = this.make_attach_control("#exit-dashboard-image-control", "Exit Dashboard Image");
		this.exit_condition_image_control = this.make_attach_control("#exit-condition-image-control", "Vehicle Condition");
	}

	make_attach_control(selector, label) {
		return frappe.ui.form.make_control({
			parent: this.wrapper.find(selector),
			df: {
				fieldname: frappe.scrub(label),
				fieldtype: "Attach Image",
				label,
			},
			render_input: true,
		});
	}

	bind_events() {
		this.wrapper.on("click", "#submit-car-entry", () => this.submit_entry());
		this.wrapper.on("click", "#submit-car-exit", () => this.submit_exit());
		this.wrapper.on("change", "#car-exit-record", () => this.update_active_meta());
	}

	load_dashboard() {
		frappe.call({
			method: "numerouno.numerouno.page.car_dashboard.car_dashboard.get_dashboard_data",
			freeze: true,
			callback: ({ message }) => {
				const data = message || {};
				this.active_entries = data.active_entries || [];
				this.render_active_entries();
				this.render_logs(data.logs || []);
			},
		});
	}

	render_active_entries() {
		const select = this.wrapper.find("#car-exit-record");
		const options = ['<option value="">Select Active Car</option>'];
		(this.active_entries || []).forEach((row) => {
			const label = `${row.vehicle} - ${row.driver_label || row.driver_name} - Odo In ${row.entry_odometer} (${row.name})`;
			options.push(`<option value="${frappe.utils.escape_html(row.name)}">${frappe.utils.escape_html(label)}</option>`);
		});
		select.html(options.join(""));
		this.update_active_meta();
		this.wrapper.find("#submit-car-exit").prop("disabled", !(this.active_entries || []).length);
	}

	update_active_meta() {
		const name = this.wrapper.find("#car-exit-record").val();
		const info = (this.active_entries || []).find((row) => row.name === name);
		const meta = this.wrapper.find("#car-active-meta");
		console.log("[car-dashboard] active entries", this.active_entries || []);

		if (!this.active_entries.length) {
			console.log("[car-dashboard] no active entries available");
			meta.text("No active car entry is open right now. Create a new entry before submitting an exit.");
			return;
		}

		if (!info) {
			console.log("[car-dashboard] no active selection made");
			meta.text("Choose an active car to see the entry odometer.");
			return;
		}

		console.log("[car-dashboard] selected active entry", info);
		meta.text(`Selected: ${info.vehicle} | Driver: ${info.driver_label || info.driver_name} | Odometer In: ${info.entry_odometer}`);
	}

	render_logs(rows) {
		const headers = ["ID", "Car", "Driver", "Odo In", "Odo Out", "Entry Time", "Exit Time", "Entry Img", "Vehicle Condition Entry", "Exit Img", "Vehicle Condition Exit"];
		const body = rows.length
			? rows.map((row) => `
				<tr>
					<td>${frappe.utils.escape_html(row.name || "")}</td>
					<td>${frappe.utils.escape_html(row.vehicle || "")}</td>
					<td>${frappe.utils.escape_html(row.driver_label || row.driver_name || "")}</td>
					<td>${frappe.utils.escape_html(String(row.entry_odometer || 0))}</td>
					<td>${frappe.utils.escape_html(row.exit_odometer ? String(row.exit_odometer) : "-")}</td>
					<td>${frappe.utils.escape_html(row.entry_stamp || "-")}</td>
					<td>${frappe.utils.escape_html(row.exit_stamp || "-")}</td>
					<td>${this.image_link(row.entry_dashboard_image, "Entry Image")}</td>
					<td>${this.image_link(row.entry_vehicle_condition_image, "Condition Entry")}</td>
					<td>${this.image_link(row.exit_dashboard_image, "Exit Image")}</td>
					<td>${this.image_link(row.exit_vehicle_condition_image, "Condition Exit")}</td>
				</tr>
			`).join("")
			: `<tr><td colspan="11" class="car-empty">No vehicle movement records yet</td></tr>`;

		this.wrapper.find("#car-log-table").html(`
			<div class="car-log-table-wrap">
				<table class="car-log-table">
					<thead>
						<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
					</thead>
					<tbody>${body}</tbody>
				</table>
			</div>
		`);
	}

	image_link(url, label) {
		if (!url) return "-";
		return `<a href="${encodeURI(url)}" target="_blank" rel="noopener noreferrer">${frappe.utils.escape_html(label)}</a>`;
	}

	submit_entry() {
		const vehicle = this.entry_vehicle_control.get_value();
		const driver_name = this.entry_driver_control.get_value();
		const entry_odometer = this.wrapper.find("#car-entry-odometer").val();

		frappe.call({
			method: "numerouno.numerouno.page.car_dashboard.car_dashboard.submit_entry",
			args: {
				vehicle,
				driver_name,
				entry_odometer,
				entry_dashboard_image: this.entry_dashboard_image_control.get_value(),
				entry_vehicle_condition_image: this.entry_condition_image_control.get_value(),
			},
			freeze: true,
			callback: ({ message }) => {
				frappe.show_alert({ message: __("Entry recorded for {0}", [message.name]), indicator: "green" });
				this.reset_entry_form();
				this.load_dashboard();
			},
		});
	}

	submit_exit() {
		const name = this.wrapper.find("#car-exit-record").val();
		const exit_odometer = this.wrapper.find("#car-exit-odometer").val();
		const selected = (this.active_entries || []).find((row) => row.name === name);
		console.log("[car-dashboard] submit_exit payload", {
			name,
			exit_odometer,
			selected,
			exit_dashboard_image: this.exit_dashboard_image_control.get_value(),
			exit_vehicle_condition_image: this.exit_condition_image_control.get_value(),
		});

		frappe.call({
			method: "numerouno.numerouno.page.car_dashboard.car_dashboard.submit_exit",
			args: {
				name,
				exit_odometer,
				exit_dashboard_image: this.exit_dashboard_image_control.get_value(),
				exit_vehicle_condition_image: this.exit_condition_image_control.get_value(),
			},
			freeze: true,
			callback: ({ message }) => {
				console.log("[car-dashboard] submit_exit success", message);
				frappe.show_alert({ message: __("Exit recorded for {0}", [message.name]), indicator: "green" });
				this.reset_exit_form();
				this.load_dashboard();
			},
			error: (error) => {
				console.log("[car-dashboard] submit_exit error", error);
			},
		});
	}

	reset_entry_form() {
		this.entry_vehicle_control.set_value("");
		this.entry_driver_control.set_value("");
		this.wrapper.find("#car-entry-odometer").val("");
		this.entry_dashboard_image_control.set_value("");
		this.entry_condition_image_control.set_value("");
	}

	reset_exit_form() {
		this.wrapper.find("#car-exit-record").val("");
		this.wrapper.find("#car-exit-odometer").val("");
		this.exit_dashboard_image_control.set_value("");
		this.exit_condition_image_control.set_value("");
	}

	inject_styles() {
		if (document.getElementById("car-dashboard-styles")) return;

		const style = document.createElement("style");
		style.id = "car-dashboard-styles";
		style.textContent = `
			.car-dashboard {
				--car-navy: #163047;
				--car-ink: #10283a;
				--car-sand: #f7f1e8;
				--car-card: rgba(255, 255, 255, 0.84);
				--car-border: rgba(22, 48, 71, 0.12);
				--car-entry: #1d6f6a;
				--car-entry-soft: #dff6f1;
				--car-exit: #d17a1d;
				--car-exit-soft: #fff1df;
				--car-log: #315c95;
				--car-log-soft: #e8f0ff;
				background:
					radial-gradient(circle at top left, rgba(209, 122, 29, 0.22), transparent 26%),
					radial-gradient(circle at top right, rgba(29, 111, 106, 0.24), transparent 24%),
					linear-gradient(180deg, #f5efe6 0%, #eef5f8 52%, #e7eef3 100%);
				min-height: calc(100vh - 120px);
				padding: 24px 12px 40px;
			}
			.car-dashboard-shell {
				max-width: 1200px;
				margin: 0 auto;
				background: rgba(255, 255, 255, 0.62);
				border: 1px solid rgba(255, 255, 255, 0.72);
				border-radius: 30px;
				padding: 28px 24px;
				box-shadow: 0 24px 60px rgba(16, 40, 58, 0.14);
				backdrop-filter: blur(8px);
			}
			.car-dashboard-header {
				text-align: center;
				margin-bottom: 22px;
			}
			.car-dashboard-header h1 {
				margin: 0;
				font-size: 42px;
				font-weight: 800;
				color: var(--car-ink);
				letter-spacing: -0.03em;
			}
			.car-dashboard-header p {
				margin: 10px 0 0;
				color: #56687a;
				font-size: 18px;
			}
			.car-dashboard-summary {
				display: grid;
				grid-template-columns: repeat(3, minmax(0, 1fr));
				gap: 16px;
				margin-bottom: 24px;
			}
			.car-summary-card {
				padding: 18px 18px 16px;
				border-radius: 20px;
				border: 1px solid var(--car-border);
				background: var(--car-card);
				box-shadow: 0 12px 28px rgba(16, 40, 58, 0.08);
			}
			.car-summary-entry {
				background: linear-gradient(135deg, var(--car-entry-soft) 0%, rgba(255,255,255,0.95) 100%);
			}
			.car-summary-exit {
				background: linear-gradient(135deg, var(--car-exit-soft) 0%, rgba(255,255,255,0.95) 100%);
			}
			.car-summary-log {
				background: linear-gradient(135deg, var(--car-log-soft) 0%, rgba(255,255,255,0.95) 100%);
			}
			.car-summary-label {
				font-size: 13px;
				font-weight: 800;
				text-transform: uppercase;
				letter-spacing: 0.08em;
				color: #5b6b79;
				margin-bottom: 8px;
			}
			.car-summary-text {
				font-size: 16px;
				line-height: 1.6;
				color: #203648;
			}
			.car-dashboard-grid {
				display: grid;
				grid-template-columns: repeat(2, minmax(0, 1fr));
				gap: 28px;
				margin-bottom: 26px;
			}
			.car-panel,
			.car-log-panel {
				background: var(--car-card);
				border: 1px solid var(--car-border);
				border-radius: 24px;
				padding: 20px;
				box-shadow: 0 16px 36px rgba(16, 40, 58, 0.09);
			}
			.car-panel-entry {
				background: linear-gradient(180deg, rgba(223, 246, 241, 0.95) 0%, rgba(255, 255, 255, 0.96) 100%);
			}
			.car-panel-exit {
				background: linear-gradient(180deg, rgba(255, 241, 223, 0.95) 0%, rgba(255, 255, 255, 0.96) 100%);
			}
			.car-panel-title,
			.car-log-title {
				font-size: 28px;
				font-weight: 800;
				color: var(--car-ink);
				margin-bottom: 16px;
				letter-spacing: -0.02em;
			}
			.car-field {
				margin-bottom: 14px;
			}
			.car-field label,
			.car-panel .control-label {
				display: block;
				color: var(--car-ink);
				font-weight: 700;
				margin-bottom: 8px;
				font-size: 16px;
			}
			.car-panel .form-control {
				height: 44px;
				font-size: 17px;
				border-radius: 12px;
				background: rgba(255, 255, 255, 0.94);
				border: 1px solid rgba(16, 40, 58, 0.14);
				box-shadow: inset 0 1px 2px rgba(16, 40, 58, 0.04);
			}
			.car-panel .form-control:focus {
				border-color: #5b8fbd;
				box-shadow: 0 0 0 3px rgba(91, 143, 189, 0.18);
			}
			.car-panel .frappe-control[data-fieldtype="Attach Image"] .form-control {
				height: auto;
			}
			.car-panel .attached-file-link,
			.car-panel .btn-attach {
				color: var(--car-ink);
			}
			.car-submit {
				width: 100%;
				height: 46px;
				border: 0;
				border-radius: 14px;
				font-size: 20px;
				font-weight: 800;
				margin-top: 10px;
				box-shadow: 0 14px 28px rgba(16, 40, 58, 0.14);
			}
			.car-submit:disabled {
				opacity: 0.55;
				cursor: not-allowed;
				box-shadow: none;
			}
			#submit-car-entry {
				background: linear-gradient(135deg, #1d6f6a 0%, #2d8b85 100%);
				color: #fff;
			}
			#submit-car-exit {
				background: linear-gradient(135deg, #d17a1d 0%, #e39a3c 100%);
				color: #1b1308;
			}
			.car-active-meta {
				margin: -2px 0 14px;
				padding: 12px 14px;
				border-radius: 12px;
				background: rgba(209, 122, 29, 0.1);
				border: 1px solid rgba(209, 122, 29, 0.2);
				color: #6f4a17;
				font-size: 14px;
				font-weight: 600;
				line-height: 1.5;
			}
			.car-log-table-wrap {
				overflow-x: auto;
				background: #fff;
				border-radius: 16px;
				border: 1px solid rgba(16, 40, 58, 0.1);
			}
			.car-log-table {
				width: 100%;
				border-collapse: collapse;
				min-width: 1100px;
			}
			.car-log-table th,
			.car-log-table td {
				border: 1px solid #d0d5dd;
				padding: 12px 10px;
				text-align: left;
				background: #fff;
			}
			.car-log-table th {
				background: linear-gradient(180deg, #f6efe7 0%, #edf5fb 100%);
				font-weight: 800;
				color: var(--car-ink);
			}
			.car-log-table tbody tr:nth-child(even) td {
				background: #fbfcfd;
			}
			.car-log-table a {
				color: #2f5d93;
				font-weight: 700;
			}
			.car-empty {
				text-align: center;
				color: #667085;
				font-size: 17px;
			}
			@media (max-width: 991px) {
				.car-dashboard-summary,
				.car-dashboard-grid {
					grid-template-columns: 1fr;
				}
			}
		`;
		document.head.appendChild(style);
	}
}
