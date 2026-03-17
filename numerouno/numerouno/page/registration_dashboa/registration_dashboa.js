frappe.pages["registration-dashboa"].on_page_load = function (wrapper) {
	if (!wrapper.registrationDashboard) {
		wrapper.registrationDashboard = new RegistrationDashboard(wrapper);
	}
};

frappe.pages["registration-dashboa"].refresh = function (wrapper) {
	wrapper.registrationDashboard?.refresh();
};

class RegistrationDashboard {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: "Registration Dashboard",
			single_column: true,
		});

		this.page.set_primary_action(__("View All Submissions"), () => {
			frappe.set_route("List", "Registration");
		});

		this.page.set_secondary_action(__("New Registration"), () => {
			frappe.new_doc("Registration");
		});

		this.inject_style();
		this.page.main.html(this.get_template());
		this.$root = $(this.page.main).find(".registration-admin-page");
		this.$summary = this.$root.find('[data-region="summary"]');
		this.$products = this.$root.find('[data-region="products"]');
		this.$recent = this.$root.find('[data-region="recent"]');
		this.$status = this.$root.find('[data-region="status"]');

		this.refresh();
	}

	inject_style() {
		if ($("#registration-dashboard-style").length) {
			return;
		}

		$(`<style id="registration-dashboard-style">
			.registration-admin-page {
				--reg-bg: linear-gradient(180deg, #fffdf8 0%, #f8fbff 100%);
				--reg-panel: #ffffff;
				--reg-border: #e7eaf0;
				--reg-ink: #14213d;
				--reg-muted: #667085;
				--reg-blue: #2563eb;
				--reg-blue-soft: #e8f0ff;
				--reg-gold: #f59e0b;
				--reg-gold-soft: #fff4d6;
				--reg-green: #16a34a;
				--reg-green-soft: #e9f9ef;
				--reg-red: #dc2626;
				--reg-red-soft: #fdecec;
				--reg-slate-soft: #f5f7fb;
				background: var(--reg-bg);
				padding: 24px;
				border-radius: 18px;
				color: var(--reg-ink);
			}
			.registration-admin-page .reg-header {
				display: flex;
				justify-content: space-between;
				align-items: flex-start;
				gap: 18px;
				margin-bottom: 20px;
			}
			.registration-admin-page .reg-title {
				font-size: 32px;
				font-weight: 700;
				margin: 0;
			}
			.registration-admin-page .reg-subtitle {
				font-size: 14px;
				color: var(--reg-muted);
				margin-top: 6px;
			}
			.registration-admin-page .reg-pillbar {
				display: flex;
				gap: 8px;
				flex-wrap: wrap;
				margin-top: 12px;
			}
			.registration-admin-page .reg-pill {
				background: #fff;
				border: 1px solid var(--reg-border);
				border-radius: 999px;
				padding: 8px 14px;
				font-size: 12px;
				color: var(--reg-muted);
			}
			.registration-admin-page .reg-grid {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 14px;
				margin-bottom: 22px;
			}
			.registration-admin-page .reg-card,
			.registration-admin-page .reg-panel {
				background: var(--reg-panel);
				border: 1px solid var(--reg-border);
				border-radius: 16px;
				box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
			}
			.registration-admin-page .reg-card {
				padding: 18px 20px;
			}
			.registration-admin-page .reg-card.pending {
				background: linear-gradient(180deg, #fffdf7 0%, var(--reg-gold-soft) 100%);
				border-color: #f7d98a;
			}
			.registration-admin-page .reg-card.approved {
				background: linear-gradient(180deg, #fafffc 0%, var(--reg-green-soft) 100%);
				border-color: #b8e7c8;
			}
			.registration-admin-page .reg-card.rejected {
				background: linear-gradient(180deg, #fffafa 0%, var(--reg-red-soft) 100%);
				border-color: #f3c2c2;
			}
			.registration-admin-page .reg-card.flagged {
				background: linear-gradient(180deg, #fbfcff 0%, var(--reg-blue-soft) 100%);
				border-color: #c6d5ff;
			}
			.registration-admin-page .reg-label {
				font-size: 13px;
				color: var(--reg-muted);
				margin-bottom: 10px;
			}
			.registration-admin-page .reg-value {
				font-size: 20px;
				font-weight: 700;
			}
			.registration-admin-page .reg-split {
				display: grid;
				grid-template-columns: 1.3fr 1fr;
				gap: 16px;
			}
			.registration-admin-page .reg-panel {
				padding: 20px;
				margin-bottom: 16px;
			}
			.registration-admin-page .reg-panel h3 {
				margin: 0 0 14px;
				font-size: 22px;
			}
			.registration-admin-page .reg-note {
				color: var(--reg-muted);
				font-size: 13px;
				margin-bottom: 16px;
			}
			.registration-admin-page .reg-statuslist,
			.registration-admin-page .reg-productlist {
				display: grid;
				gap: 10px;
			}
			.registration-admin-page .reg-row {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 12px;
				padding: 12px 14px;
				background: var(--reg-slate-soft);
				border-radius: 12px;
			}
			.registration-admin-page .reg-row strong {
				display: block;
				font-size: 14px;
				margin-bottom: 3px;
			}
			.registration-admin-page .reg-row span {
				color: var(--reg-muted);
				font-size: 12px;
			}
			.registration-admin-page .reg-badge {
				display: inline-flex;
				align-items: center;
				justify-content: center;
				padding: 4px 10px;
				border-radius: 999px;
				font-size: 11px;
				font-weight: 700;
				text-transform: uppercase;
			}
			.registration-admin-page .reg-badge.pending { background: var(--reg-gold-soft); color: #9a6700; }
			.registration-admin-page .reg-badge.approved { background: var(--reg-green-soft); color: #0f7a33; }
			.registration-admin-page .reg-badge.rejected { background: var(--reg-red-soft); color: #b42318; }
			.registration-admin-page .reg-badge.flagged { background: var(--reg-blue-soft); color: #1d4ed8; }
			.registration-admin-page table {
				width: 100%;
				border-collapse: collapse;
			}
			.registration-admin-page th,
			.registration-admin-page td {
				padding: 14px 10px;
				border-bottom: 1px solid var(--reg-border);
				text-align: left;
				font-size: 13px;
				vertical-align: top;
			}
			.registration-admin-page th {
				font-size: 12px;
				color: var(--reg-muted);
				font-weight: 600;
				text-transform: uppercase;
				letter-spacing: 0.04em;
			}
			.registration-admin-page .reg-empty {
				padding: 18px;
				text-align: center;
				color: var(--reg-muted);
				background: var(--reg-slate-soft);
				border-radius: 12px;
				font-size: 13px;
			}
			@media (max-width: 991px) {
				.registration-admin-page .reg-split {
					grid-template-columns: 1fr;
				}
			}
		</style>`).appendTo("head");
	}

	get_template() {
		return `
			<div class="registration-admin-page">
				<div class="reg-header">
					<div>
						<div class="reg-title">Admin Panel</div>
						<div class="reg-subtitle">Registration oversight for OPITO learner submissions stored in the Registration DocType.</div>
						<div class="reg-pillbar">
							<div class="reg-pill">Dashboard</div>
							<div class="reg-pill">Submissions</div>
							<div class="reg-pill">Settings</div>
						</div>
					</div>
				</div>

				<div class="reg-grid" data-region="summary"></div>

				<div class="reg-split">
					<div>
						<div class="reg-panel">
							<h3>Recent Submissions</h3>
							<div class="reg-note">Latest registration records with learner, status, and creation details.</div>
							<div data-region="recent"></div>
						</div>
					</div>
					<div>
						<div class="reg-panel">
							<h3>Status Overview</h3>
							<div class="reg-note">Quick operational view of the current registration queue.</div>
							<div data-region="status"></div>
						</div>
						<div class="reg-panel">
							<h3>Products</h3>
							<div class="reg-note">Submission counts by registered product title.</div>
							<div data-region="products"></div>
						</div>
					</div>
				</div>
			</div>
		`;
	}

	refresh() {
		frappe.call({
			method: "numerouno.numerouno.page.registration_dashboa.registration_dashboa.get_registration_dashboard_data",
			freeze: false,
			callback: (r) => {
				if (!r.message) {
					return;
				}
				this.render(r.message);
			},
			error: () => {
				frappe.show_alert({ message: __("Unable to load registration dashboard"), indicator: "red" });
			},
		});
	}

	render(data) {
		this.render_summary(data.summary || {});
		this.render_status(data.status_rows || []);
		this.render_products(data.products || []);
		this.render_recent(data.recent_submissions || []);
	}

	render_summary(summary) {
		const cards = [
			{ label: "Total Submissions", value: summary.total_submissions || 0, cls: "" },
			{ label: "Pending", value: summary.pending || 0, cls: "pending" },
			{ label: "Approved", value: summary.approved || 0, cls: "approved" },
			{ label: "Rejected", value: summary.rejected || 0, cls: "rejected" },
			{ label: "Abnormal / Flagged", value: summary.flagged || 0, cls: "flagged" },
			{ label: "Today's Submissions", value: summary.today || 0, cls: "" },
			{ label: "This Week", value: summary.this_week || 0, cls: "" },
		];

		this.$summary.html(cards.map((card) => `
			<div class="reg-card ${card.cls}">
				<div class="reg-label">${frappe.utils.escape_html(card.label)}</div>
				<div class="reg-value">${format_number(card.value || 0, null, 0)}</div>
			</div>
		`).join(""));
	}

	render_status(rows) {
		if (!rows.length) {
			this.$status.html('<div class="reg-empty">No registration statuses to show yet.</div>');
			return;
		}

		this.$status.html(`
			<div class="reg-statuslist">
				${rows.map((row) => `
					<div class="reg-row">
						<div>
							<strong>${frappe.utils.escape_html(row.label)}</strong>
							<span>${frappe.utils.escape_html(row.note || "")}</span>
						</div>
						<div class="reg-badge ${frappe.scrub(row.label)}">${format_number(row.count || 0, null, 0)}</div>
					</div>
				`).join("")}
			</div>
		`);
	}

	render_products(products) {
		if (!products.length) {
			this.$products.html('<div class="reg-empty">No product activity found yet.</div>');
			return;
		}

		this.$products.html(`
			<div class="reg-productlist">
				${products.map((product) => `
					<div class="reg-row">
						<div>
							<strong>${frappe.utils.escape_html(product.product_title || "Unspecified Product")}</strong>
							<span>${frappe.utils.escape_html(product.last_submission || "No recent submission date")}</span>
						</div>
						<div class="reg-value" style="font-size: 18px;">${format_number(product.total || 0, null, 0)}</div>
					</div>
				`).join("")}
			</div>
		`);
	}

	render_recent(rows) {
		if (!rows.length) {
			this.$recent.html('<div class="reg-empty">No submissions available yet.</div>');
			return;
		}

		this.$recent.html(`
			<table>
				<thead>
					<tr>
						<th>Submission #</th>
						<th>Product</th>
						<th>Learner</th>
						<th>Status</th>
						<th>Date</th>
						<th>Action</th>
					</tr>
				</thead>
				<tbody>
					${rows.map((row) => `
						<tr>
							<td>${frappe.utils.escape_html(row.name)}</td>
							<td>${frappe.utils.escape_html(row.product_title || "")}</td>
							<td>${frappe.utils.escape_html(row.full_name || row.learner_surname || "")}</td>
							<td><span class="reg-badge ${frappe.scrub(row.registration_status || "pending")}">${frappe.utils.escape_html(row.registration_status || "Pending")}</span></td>
							<td>${frappe.utils.escape_html(row.creation_label || "")}</td>
							<td><a href="/app/registration/${encodeURIComponent(row.name)}">View</a></td>
						</tr>
					`).join("")}
				</tbody>
			</table>
		`);
	}
}
