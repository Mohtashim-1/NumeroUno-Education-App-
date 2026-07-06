frappe.pages["driver-invoice-portal"].on_page_load = function (wrapper) {
	new DriverInvoicePortal(wrapper);
};

class DriverInvoicePortal {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Driver Invoice Portal"),
			single_column: true,
		});
		this.view = "list";
		this.selected_invoice = null;
		this.signature_data = "";
		this.selected_invoices = new Set();
		this.delivery_queue = [];
		this.inject_pwa_meta();
		this.render();
		this.bind_events();
		this.load_kpis();
		this.load_active_tab();
	}

	load_active_tab() {
		if (this.active_tab === "completed") this.load_completed();
		else this.load_pending();
	}

	load_kpis() {
		frappe.call({
			method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_portal_kpis",
			callback: (r) => {
				if (r.exc) return;
				const k = r.message || {};
				this.portal_meta = k;
				this.wrapper.find("#dip-metric-pending").text(k.pending || 0);
				this.wrapper.find("#dip-metric-done").text(k.completed || 0);
				this.wrapper.find("#dip-metric-today").text(k.completed_today || 0);
				if (k.driver_only) {
					this.wrapper.find("#dip-metric-assigned-wrap, #dip-metric-unassigned-wrap").hide();
					this.wrapper.find("#dip-driver-banner").html(`
						<strong>${__("Driver")}:</strong> ${frappe.utils.escape_html(k.driver_name || k.user)}
						<div class="dip-banner-note">${__("Select invoices and tap Deliver Selected.")}</div>
					`).show();
					this.wrapper.find("#dip-bulk-deliver").removeAttr("hidden");
					this.wrapper.find("#dip-assign-controls").attr("hidden", true);
				} else {
					this.wrapper.find("#dip-driver-banner").hide();
					this.wrapper.find("#dip-metric-assigned-wrap").show();
					this.wrapper.find("#dip-metric-assigned").text(k.assigned_pending || 0);
					this.wrapper.find("#dip-metric-unassigned").text(k.unassigned_pending || 0);
					if (k.can_assign_driver) {
						this.wrapper.find("#dip-assign-controls").removeAttr("hidden");
						this.setup_driver_picker();
					} else {
						this.wrapper.find("#dip-assign-controls").attr("hidden", true);
					}
					this.wrapper.find("#dip-bulk-deliver").removeAttr("hidden");
				}
				this.update_bulk_bar();
			},
		});
	}

	setup_driver_picker() {
		if (this.driver_control) return;
		this.driver_control = frappe.ui.form.make_control({
			parent: this.wrapper.find("#dip-driver-picker")[0],
			df: {
				fieldtype: "Link",
				options: "User",
				label: __("Delivery Driver"),
				placeholder: __("Choose driver"),
				get_query() {
					return {
						query: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_delivery_driver_users",
					};
				},
			},
			render_input: true,
		});
		this.driver_control.refresh();
	}

	inject_pwa_meta() {
		if (document.querySelector('meta[name="apple-mobile-web-app-capable"]')) return;
		const head = document.head;
		[
			["name", "apple-mobile-web-app-capable", "yes"],
			["name", "apple-mobile-web-app-status-bar-style", "default"],
			["name", "mobile-web-app-capable", "yes"],
			["name", "theme-color", "#155e75"],
		].forEach(([attr, key, value]) => {
			const meta = document.createElement("meta");
			meta.setAttribute(attr, key);
			meta.content = value;
			head.appendChild(meta);
		});
	}

	render() {
		this.wrapper.find(".layout-main-section").html(`
			<div class="dip-portal">
				<div class="dip-shell">
				<div class="dip-hero">
					<div class="dip-hero-copy">
						<h1>${__("Invoice Delivery")}</h1>
						<p>${__("Select invoices below, assign a delivery driver, then the driver acknowledges delivery here.")}</p>
						<div class="dip-driver-banner" id="dip-driver-banner" hidden></div>
					</div>
					<div class="dip-metrics">
						<div class="dip-metric dip-metric-pending"><span>${__("My Pending")}</span><strong id="dip-metric-pending">0</strong></div>
						<div class="dip-metric dip-metric-done"><span>${__("Completed")}</span><strong id="dip-metric-done">0</strong></div>
						<div class="dip-metric dip-metric-today"><span>${__("Today")}</span><strong id="dip-metric-today">0</strong></div>
						<div class="dip-metric dip-metric-assigned" id="dip-metric-assigned-wrap"><span>${__("Assigned")}</span><strong id="dip-metric-assigned">0</strong></div>
						<div class="dip-metric dip-metric-unassigned" id="dip-metric-unassigned-wrap"><span>${__("Unassigned")}</span><strong id="dip-metric-unassigned">0</strong></div>
					</div>
				</div>

				<div class="dip-toolbar">
					<input type="search" class="dip-search" id="dip-search" placeholder="${__("Search invoice or customer...")}">
					<button type="button" class="dip-btn dip-btn-ghost" id="dip-refresh">${__("Refresh")}</button>
				</div>

				<div class="dip-tabs">
					<button type="button" class="dip-tab active" data-tab="pending">${__("Pending")}</button>
					<button type="button" class="dip-tab" data-tab="completed">${__("Completed")}</button>
				</div>

				<div class="dip-bulk-bar" id="dip-bulk-bar">
					<div class="dip-bulk-left">
						<label class="dip-bulk-select-all">
							<input type="checkbox" id="dip-select-all">
							<span>${__("Select all on page")}</span>
						</label>
						<span class="dip-bulk-count" id="dip-selected-count">${__("Select invoices below")}</span>
					</div>
					<div class="dip-assign-controls" id="dip-assign-controls" hidden>
						<div class="dip-driver-picker-wrap" id="dip-driver-picker"></div>
						<button type="button" class="dip-btn dip-btn-primary dip-btn-small" id="dip-assign-selected">${__("Assign Driver")}</button>
						<button type="button" class="dip-btn dip-btn-ghost dip-btn-small" id="dip-clear-driver">${__("Clear Driver")}</button>
					</div>
					<div class="dip-bulk-actions">
						<button type="button" class="dip-btn dip-btn-primary dip-btn-small" id="dip-bulk-deliver" hidden>${__("Deliver Selected")}</button>
					</div>
				</div>

				<div id="dip-list-view" class="dip-list"></div>
				<div class="dip-list-footer" id="dip-list-footer" hidden>
					<span id="dip-list-count"></span>
					<button type="button" class="dip-btn dip-btn-ghost dip-btn-small" id="dip-load-more">${__("Load More")}</button>
				</div>

				<div id="dip-form-view" class="dip-form" hidden>
					<button type="button" class="dip-back" id="dip-back">&larr; ${__("Back to list")}</button>
					<div class="dip-form-layout">
						<div class="dip-invoice-card" id="dip-invoice-summary"></div>

						<div class="dip-section">
							<h3>${__("Acknowledgement Details")}</h3>
							<p class="dip-help">${__("Document Inside")}</p>
							<div class="dip-checks">
								<label class="dip-check"><input type="checkbox" id="dip-has-certificates"> ${__("Certificates")}</label>
								<label class="dip-check"><input type="checkbox" id="dip-has-cards"> ${__("Cards")}</label>
							</div>
							<div class="dip-form-fields-grid">
								<label class="dip-field">
									<span>${__("Name of Receiver")} *</span>
									<input type="text" id="dip-receiver-name" class="dip-input" autocomplete="name">
								</label>
								<label class="dip-field">
									<span>${__("Date of Receiving")} *</span>
									<input type="date" id="dip-receiving-date" class="dip-input">
								</label>
								<label class="dip-field dip-field-full">
									<span>${__("Contact No.")}</span>
									<input type="tel" id="dip-contact-no" class="dip-input" autocomplete="tel">
								</label>
								<div class="dip-field dip-field-full dip-field-signature">
									<span class="dip-field-label">${__("Receiver Signature")} *</span>
									<div class="dip-signature-wrap">
										<canvas id="dip-signature-canvas" class="dip-signature-canvas"></canvas>
										<div class="dip-signature-actions">
											<span class="dip-signature-hint">${__("Sign directly in the box above")}</span>
											<button type="button" class="dip-btn dip-btn-ghost dip-btn-small" id="dip-clear-sign" disabled>${__("Clear")}</button>
										</div>
									</div>
								</div>
								<label class="dip-field dip-field-full">
									<span>${__("Remarks")}</span>
									<textarea id="dip-remarks" class="dip-input dip-textarea" rows="2"></textarea>
								</label>
							</div>
						</div>

						<div class="dip-actions">
							<button type="button" class="dip-btn dip-btn-primary dip-btn-block" id="dip-submit">${__("Submit Acknowledgement")}</button>
						</div>
					</div>
				</div>
				</div>
			</div>
		`);
		this.inject_styles();
		this.$list = this.wrapper.find("#dip-list-view");
		this.$form = this.wrapper.find("#dip-form-view");
		this.wrapper.find("#dip-receiving-date").val(frappe.datetime.get_today());
	}

	inject_styles() {
		if (document.getElementById("dip-portal-styles")) return;
		const style = document.createElement("style");
		style.id = "dip-portal-styles";
		style.textContent = `
			.dip-portal {
				--dip-bg: #eef6f8;
				--dip-card: #ffffff;
				--dip-ink: #12313d;
				--dip-muted: #5d7280;
				--dip-line: #d5e3ea;
				--dip-accent: #155e75;
				--dip-accent-soft: #dff3f8;
				font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
				color: var(--dip-ink);
				background: linear-gradient(180deg, #e8f3f7 0%, var(--dip-bg) 40%, #f7fafb 100%);
				min-height: calc(100vh - 110px);
				padding: 16px 12px 32px;
				margin: -15px;
			}
			.dip-shell {
				width: 100%;
				max-width: 1180px;
				margin: 0 auto;
			}
			.dip-hero {
				display: grid;
				gap: 16px;
				margin-bottom: 16px;
			}
			.dip-hero h1 { margin: 0; font-size: 28px; font-weight: 800; letter-spacing: -0.03em; }
			.dip-hero p { margin: 6px 0 0; color: var(--dip-muted); font-size: 14px; line-height: 1.5; max-width: 720px; }
			.dip-driver-banner {
				margin-top: 12px;
				background: var(--dip-accent-soft);
				border: 1px solid #b9dfdc;
				border-radius: 12px;
				padding: 10px 12px;
				font-size: 14px;
				color: var(--dip-accent);
			}
			.dip-banner-note { margin-top: 4px; font-size: 12px; color: var(--dip-muted); font-weight: 600; }
			.dip-metrics {
				display: grid;
				grid-template-columns: repeat(2, minmax(0, 1fr));
				gap: 10px;
			}
			.dip-metric {
				background: var(--dip-card); border: 1px solid var(--dip-line);
				border-radius: 14px; padding: 12px 14px; box-shadow: 0 8px 24px rgba(18,49,61,.06);
			}
			.dip-metric span { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--dip-muted); }
			.dip-metric strong { font-size: 24px; line-height: 1.1; }
			.dip-metric-pending strong { color: #8a5a00; }
			.dip-metric-done strong { color: #17663a; }
			.dip-metric-today strong { color: #155e75; }
			.dip-toolbar { display: flex; gap: 8px; margin-bottom: 12px; }
			.dip-search {
				flex: 1; border: 1px solid var(--dip-line); border-radius: 12px; padding: 12px 14px;
				font-size: 16px; background: #fff;
			}
			.dip-tabs { display: flex; gap: 8px; margin-bottom: 14px; }
			.dip-tab {
				flex: 1; border: 1px solid var(--dip-line); background: #fff; border-radius: 999px;
				padding: 10px 12px; font-weight: 700; font-size: 14px; cursor: pointer;
			}
			.dip-tab.active { background: var(--dip-accent); border-color: var(--dip-accent); color: #fff; }
			.dip-list { display: grid; gap: 10px; grid-template-columns: 1fr; }
			.dip-card {
				background: var(--dip-card); border: 1px solid var(--dip-line); border-radius: 16px;
				padding: 14px 16px; box-shadow: 0 10px 24px rgba(18,49,61,.06); cursor: pointer;
				display: grid; grid-template-columns: auto 1fr; gap: 12px; align-items: start;
			}
			.dip-card-select { display: flex; padding-top: 2px; }
			.dip-card-select input { width: 18px; height: 18px; cursor: pointer; }
			.dip-card-completed { grid-template-columns: 1fr; }
			.dip-bulk-bar {
				display: none;
				align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
				background: var(--dip-card); border: 1px solid var(--dip-line); border-radius: 14px;
				padding: 12px 14px; margin-bottom: 10px;
			}
			.dip-bulk-bar.is-visible { display: flex; }
			.dip-bulk-left { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
			.dip-assign-controls {
				display: flex; align-items: flex-end; gap: 8px; flex-wrap: wrap; flex: 1;
				justify-content: flex-end;
			}
			.dip-driver-picker-wrap { min-width: 220px; max-width: 280px; }
			.dip-driver-picker-wrap .frappe-control { margin-bottom: 0; }
			.dip-card-assign {
				margin-top: 8px;
			}
			.dip-bulk-select-all {
				display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; margin: 0;
			}
			.dip-bulk-count { color: var(--dip-muted); font-size: 13px; font-weight: 600; }
			.dip-bulk-actions { display: flex; gap: 8px; margin-left: auto; flex-wrap: wrap; }
			.dip-card-top { display: flex; justify-content: space-between; gap: 10px; align-items: start; }
			.dip-card h4 { margin: 0 0 4px; font-size: 16px; }
			.dip-card p { margin: 0; color: var(--dip-muted); font-size: 13px; line-height: 1.45; }
			.dip-pill {
				display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px;
				font-size: 11px; font-weight: 700; white-space: nowrap;
			}
			.dip-pill.pending { background: #fff4df; color: #8a5a00; }
			.dip-pill.done { background: #e4f6ef; color: #17663a; }
			.dip-pill.draft { background: #eef2ff; color: #3730a3; }
			.dip-list-footer {
				display: flex;
				align-items: center;
				justify-content: space-between;
				gap: 12px;
				margin-top: 12px;
				padding: 0 4px;
				color: var(--dip-muted);
				font-size: 13px;
				font-weight: 600;
			}
			.dip-empty { text-align: center; color: var(--dip-muted); padding: 28px 12px; }
			.dip-form { display: block; }
			.dip-back {
				border: 0; background: transparent; color: var(--dip-accent); font-weight: 700;
				padding: 0 0 12px; font-size: 14px; cursor: pointer;
			}
			.dip-invoice-card, .dip-section {
				background: var(--dip-card); border: 1px solid var(--dip-line); border-radius: 16px;
				padding: 16px; margin-bottom: 12px; box-shadow: 0 10px 24px rgba(18,49,61,.06);
			}
			.dip-invoice-card { max-height: 52vh; overflow-y: auto; }
			.dip-section h3 { margin: 0 0 12px; font-size: 18px; }
			.dip-help { margin: 0 0 10px; color: var(--dip-muted); font-size: 13px; font-weight: 700; }
			.dip-checks { display: flex; gap: 16px; margin-bottom: 14px; flex-wrap: wrap; }
			.dip-check { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; }
			.dip-check input { width: 18px; height: 18px; }
			.dip-field { display: block; margin-bottom: 0; }
			.dip-form-fields-grid { display: grid; gap: 12px; margin-top: 12px; }
			.dip-field-full { grid-column: 1 / -1; }
			.dip-field > span, .dip-field-label {
				display: block; margin-bottom: 6px; font-size: 12px; font-weight: 700;
				text-transform: uppercase; letter-spacing: .06em; color: var(--dip-muted);
			}
			.dip-input, .dip-textarea {
				width: 100%; border: 1px solid var(--dip-line); border-radius: 12px; padding: 12px 14px;
				font-size: 16px; background: #fff;
			}
			.dip-signature-wrap { display: grid; gap: 6px; }
			.dip-signature-canvas {
				width: 100%; height: 130px; display: block;
				border: 2px dashed var(--dip-line); border-radius: 12px; background: #fbfeff;
				touch-action: none; cursor: crosshair;
				user-select: none;
			}
			.dip-signature-actions {
				display: flex; align-items: center; justify-content: space-between; gap: 8px;
			}
			.dip-signature-hint { color: var(--dip-muted); font-size: 12px; font-weight: 600; }
			.dip-actions { position: sticky; bottom: 8px; padding-top: 4px; }
			.dip-btn {
				border: 0; border-radius: 12px; padding: 12px 16px; font-size: 14px; font-weight: 700; cursor: pointer;
			}
			.dip-btn-small { padding: 8px 12px; font-size: 13px; }
			.dip-btn-primary { background: var(--dip-accent); color: #fff; }
			.dip-btn-ghost { background: #fff; color: var(--dip-ink); border: 1px solid var(--dip-line); }
			.dip-btn-block { width: 100%; }
			.dip-summary-row { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; font-size: 14px; }
			.dip-summary-row strong { text-align: right; }
			.dip-summary-block { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--dip-line); }
			.dip-summary-block pre { margin: 0; white-space: pre-wrap; font-family: inherit; font-size: 13px; color: var(--dip-muted); }
			.dip-form-view[hidden], .dip-form[hidden] { display: none !important; }
			.dip-form-layout {
				display: grid;
				gap: 12px;
			}
			@media (min-width: 600px) {
				.dip-form-fields-grid {
					grid-template-columns: 1fr 1fr;
				}
			}
			@media (min-width: 900px) {
				.dip-hero {
					grid-template-columns: minmax(320px, 1.1fr) minmax(360px, 1fr);
					align-items: start;
				}
				.dip-metrics {
					grid-template-columns: repeat(3, minmax(0, 1fr));
				}
				.dip-list {
					grid-template-columns: repeat(2, minmax(0, 1fr));
				}
				.dip-form-layout {
					grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
					align-items: start;
				}
				.dip-actions {
					grid-column: 1 / -1;
					max-width: 420px;
				}
				.dip-invoice-card { max-height: none; }
			}
			@media (min-width: 1200px) {
				.dip-portal { padding: 24px 20px 40px; }
				.dip-metrics {
					grid-template-columns: repeat(5, minmax(0, 1fr));
				}
				.dip-list {
					grid-template-columns: repeat(3, minmax(0, 1fr));
				}
			}
			@media (max-width: 899px) {
				#dip-metric-unassigned-wrap { display: none; }
			}
		`;
		document.head.appendChild(style);
	}

	bind_events() {
		const self = this;
		this.active_tab = "pending";
		this.wrapper.find("#dip-refresh").on("click", () => {
			this.load_kpis();
			this.load_active_tab();
		});
		this.wrapper.find("#dip-search").on("input", frappe.utils.debounce(() => {
			if (this.active_tab === "completed") return;
			this.load_pending(this.wrapper.find("#dip-search").val());
		}, 300));
		this.wrapper.find(".dip-tab").on("click", function () {
			self.wrapper.find(".dip-tab").removeClass("active");
			$(this).addClass("active");
			self.active_tab = $(this).data("tab");
			self.wrapper.find(".dip-toolbar").toggle(self.active_tab !== "completed");
			self.clear_selection();
			self.load_active_tab();
		});
		this.wrapper.find("#dip-back").on("click", () => this.show_list());
		this._clear_sign_pointer_id = null;
		this.wrapper.find("#dip-clear-sign").on("pointerdown", (e) => {
			e.preventDefault();
			e.stopPropagation();
			if ($(e.currentTarget).prop("disabled")) return;
			this._clear_sign_pointer_id = e.pointerId;
		});
		this.wrapper.find("#dip-clear-sign").on("pointerup", (e) => {
			e.preventDefault();
			e.stopPropagation();
			if (e.pointerId !== this._clear_sign_pointer_id) return;
			this._clear_sign_pointer_id = null;
			if ($(e.currentTarget).prop("disabled")) return;
			dip_log("clear button pressed");
			this.set_signature("");
		});
		this.wrapper.find("#dip-submit").on("click", () => this.submit_acknowledgement());
		this.pending_rows = [];
		this.pending_offset = 0;
		this.pending_total = 0;
		this.wrapper.find("#dip-load-more").on("click", () => {
			this.load_pending(this.wrapper.find("#dip-search").val(), true);
		});
		this.wrapper.find("#dip-select-all").on("change", (e) => {
			const checked = e.currentTarget.checked;
			this.$list.find(".dip-select-invoice").each((_, el) => {
				const invoice = $(el).data("invoice");
				$(el).prop("checked", checked);
				if (checked) this.selected_invoices.add(invoice);
				else this.selected_invoices.delete(invoice);
			});
			this.update_bulk_bar();
		});
		this.wrapper.find("#dip-bulk-deliver").on("click", () => this.start_bulk_delivery());
		this.wrapper.find("#dip-assign-selected").on("click", () => this.assign_selected_driver());
		this.wrapper.find("#dip-clear-driver").on("click", () => this.clear_selected_driver());
	}

	get_selected_invoices() {
		return Array.from(this.selected_invoices);
	}

	update_bulk_bar() {
		const count = this.selected_invoices.size;
		const onPending = this.active_tab === "pending" && this.view === "list";
		this.wrapper.find("#dip-bulk-bar").toggleClass("is-visible", onPending);
		this.wrapper.find("#dip-selected-count").text(
			count
				? __("Selected: {0}", [count])
				: this.portal_meta?.can_assign_driver
					? __("Tick invoices, choose driver above, then Assign Driver")
					: __("Tick invoices, then Deliver Selected")
		);
		const pageCount = this.$list.find(".dip-select-invoice").length;
		const checkedCount = this.$list.find(".dip-select-invoice:checked").length;
		this.wrapper.find("#dip-select-all").prop("checked", pageCount > 0 && checkedCount === pageCount);
	}

	assign_selected_driver() {
		const invoices = this.get_selected_invoices();
		if (!invoices.length) {
			frappe.msgprint(__("Select at least one invoice using the checkboxes."));
			return;
		}
		const driver = this.driver_control?.get_value();
		if (!driver) {
			dip_show_assign_driver_dialog(invoices, () => this.after_assign_refresh());
			return;
		}
		frappe.call({
			method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_assign_delivery_driver",
			args: { sales_invoices: invoices, driver },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				const msg = r.message || {};
				frappe.show_alert({
					message: __("Assigned {0} invoice(s) to {1}", [msg.updated || 0, msg.driver_name || driver]),
					indicator: "green",
				});
				this.after_assign_refresh();
			},
		});
	}

	assign_single_invoice(invoice) {
		const driver = this.driver_control?.get_value();
		if (driver) {
			frappe.call({
				method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_assign_delivery_driver",
				args: { sales_invoices: [invoice], driver },
				freeze: true,
				callback: (r) => {
					if (r.exc) return;
					const msg = r.message || {};
					frappe.show_alert({
						message: __("Assigned {0} to {1}", [invoice, msg.driver_name || driver]),
						indicator: "green",
					});
					this.after_assign_refresh();
				},
			});
			return;
		}
		dip_show_assign_driver_dialog([invoice], () => this.after_assign_refresh());
	}

	clear_selected_driver() {
		const invoices = this.get_selected_invoices();
		if (!invoices.length) {
			frappe.msgprint(__("Select at least one invoice using the checkboxes."));
			return;
		}
		frappe.confirm(
			__("Clear delivery driver from {0} selected invoice(s)?", [invoices.length]),
			() => {
				frappe.call({
					method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_clear_delivery_driver",
					args: { sales_invoices: invoices },
					freeze: true,
					callback: (r) => {
						if (r.exc) return;
						frappe.show_alert({
							message: __("Cleared driver on {0} invoice(s)", [r.message?.updated || 0]),
							indicator: "green",
						});
						this.after_assign_refresh();
					},
				});
			}
		);
	}

	after_assign_refresh() {
		this.clear_selection();
		this.load_kpis();
		this.load_pending(this.wrapper.find("#dip-search").val());
	}

	clear_selection() {
		this.selected_invoices.clear();
		this.update_bulk_bar();
	}

	bulk_assign_driver() {
		this.assign_selected_driver();
	}

	start_bulk_delivery() {
		const invoices = this.get_selected_invoices();
		if (!invoices.length) {
			frappe.msgprint(__("Select at least one invoice."));
			return;
		}
		this.delivery_queue = [...invoices];
		this.open_invoice(this.delivery_queue[0]);
	}

	load_pending(search, append) {
		if (!append) {
			this.pending_offset = 0;
			this.pending_rows = [];
		}
		frappe.call({
			method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_pending_invoices",
			args: { search: search || "", limit: 50, offset: this.pending_offset },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				if (this.active_tab !== "pending") return;
				const msg = r.message || {};
				const rows = msg.rows || [];
				this.pending_total = msg.total || 0;
				this.pending_rows = append ? this.pending_rows.concat(rows) : rows;
				this.pending_offset = this.pending_rows.length;
				this.render_list(this.pending_rows, "pending");
				this.update_pending_footer();
			},
		});
	}

	update_pending_footer() {
		const $footer = this.wrapper.find("#dip-list-footer");
		if (this.active_tab !== "pending" || !this.pending_rows.length) {
			$footer.attr("hidden", true);
			return;
		}
		$footer.removeAttr("hidden");
		this.wrapper.find("#dip-list-count").text(
			__("Showing {0} of {1}", [this.pending_rows.length, this.pending_total])
		);
		this.wrapper.find("#dip-load-more").toggle(this.pending_rows.length < this.pending_total);
	}

	load_completed() {
		frappe.call({
			method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_completed_invoices",
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				if (this.active_tab !== "completed") return;
				this.wrapper.find("#dip-list-footer").attr("hidden", true);
				this.render_list(r.message.rows || [], "completed");
			},
		});
	}

	render_list(rows, mode) {
		if (!rows.length) {
			const emptyMsg =
				mode === "completed"
					? __("No completed acknowledgements yet.")
					: this.portal_meta?.driver_only
						? __("No invoices assigned to you yet. Ask Accounts to set Delivery Driver on the Sales Invoice.")
						: __("No pending invoices found.");
			this.$list.html(`<div class="dip-empty">${emptyMsg}</div>`);
			this.wrapper.find("#dip-list-footer").attr("hidden", true);
			this.update_bulk_bar();
			return;
		}

		const html = rows.map((row) => {
			if (mode === "completed") {
				const docs = [row.has_certificates ? __("Certificates") : "", row.has_cards ? __("Cards") : ""].filter(Boolean).join(", ");
				return `
					<div class="dip-card dip-card-completed" data-ack="${frappe.utils.escape_html(row.name)}">
						<div class="dip-card-top">
							<div>
								<h4>${frappe.utils.escape_html(row.sales_invoice)}</h4>
								<p>${frappe.utils.escape_html(row.customer_name || "")}</p>
								<p>${__("Receiver")}: ${frappe.utils.escape_html(row.receiver_name || "")} · ${frappe.utils.escape_html(docs)}</p>
							</div>
							<span class="dip-pill done">${__("Submitted")}</span>
						</div>
					</div>`;
			}

			const status = row.acknowledgement_status || "Pending";
			const pillClass = status === "Draft" ? "draft" : "pending";
			const driverMeta = row.delivery_driver_name
				? `<p>${__("Driver")}: ${frappe.utils.escape_html(row.delivery_driver_name)}</p>`
				: `<p>${__("Driver")}: ${__("Not assigned")}</p>`;
			const checked = this.selected_invoices.has(row.name) ? "checked" : "";
			const assignBtn = this.portal_meta?.can_assign_driver
				? `<button type="button" class="dip-btn dip-btn-ghost dip-btn-small dip-card-assign" data-invoice="${frappe.utils.escape_html(row.name)}">${__("Assign Driver")}</button>`
				: "";
			return `
				<div class="dip-card" data-invoice="${frappe.utils.escape_html(row.name)}">
					<label class="dip-card-select" onclick="event.stopPropagation()">
						<input type="checkbox" class="dip-select-invoice" data-invoice="${frappe.utils.escape_html(row.name)}" ${checked}>
					</label>
					<div class="dip-card-top">
						<div>
							<h4>${frappe.utils.escape_html(row.name)}</h4>
							<p>${frappe.utils.escape_html(row.customer_name || row.customer || "")}</p>
							<p>${frappe.datetime.str_to_user(row.posting_date)} · ${format_currency(row.grand_total, row.currency)}</p>
							${driverMeta}
							${assignBtn}
						</div>
						<span class="dip-pill ${pillClass}">${frappe.utils.escape_html(status)}</span>
					</div>
				</div>`;
		}).join("");

		this.$list.html(html);
		this.update_bulk_bar();

		this.$list.find(".dip-select-invoice").on("change", (e) => {
			e.stopPropagation();
			const invoice = $(e.currentTarget).data("invoice");
			if (e.currentTarget.checked) this.selected_invoices.add(invoice);
			else this.selected_invoices.delete(invoice);
			this.update_bulk_bar();
		});

		this.$list.find("[data-invoice]").on("click", (e) => {
			if ($(e.target).closest(".dip-card-select, .dip-card-assign").length) return;
			this.open_invoice($(e.currentTarget).data("invoice"));
		});
		this.$list.find(".dip-card-assign").on("click", (e) => {
			e.preventDefault();
			e.stopPropagation();
			this.assign_single_invoice($(e.currentTarget).data("invoice"));
		});
		this.$list.find("[data-ack]").on("click", (e) => {
			frappe.set_route("Form", "Invoice Delivery Acknowledgement", $(e.currentTarget).data("ack"));
		});
	}

	open_invoice(sales_invoice) {
		frappe.call({
			method: "numerouno.numerouno.doctype.invoice_delivery_acknowledgement.invoice_delivery_acknowledgement.get_invoice_context",
			args: { sales_invoice },
			freeze: true,
			callback: (r) => {
				if (r.exc) return;
				const data = r.message;
				if (data.already_acknowledged && data.acknowledgement) {
					frappe.msgprint(__("This invoice is already acknowledged."));
					frappe.set_route("Form", "Invoice Delivery Acknowledgement", data.acknowledgement);
					return;
				}
				this.selected_invoice = data.sales_invoice;
				this.reset_form();
				this.render_invoice_summary(data);
				this.show_form();
			},
		});
	}

	render_invoice_summary(data) {
		this.wrapper.find("#dip-invoice-summary").html(`
			<div class="dip-summary-row"><span>${__("Invoice")}</span><strong>${frappe.utils.escape_html(data.sales_invoice)}</strong></div>
			<div class="dip-summary-row"><span>${__("Customer")}</span><strong>${frappe.utils.escape_html(data.customer_name || "")}</strong></div>
			<div class="dip-summary-row"><span>${__("Date")}</span><strong>${frappe.datetime.str_to_user(data.posting_date)}</strong></div>
			<div class="dip-summary-row"><span>${__("Amount")}</span><strong>${format_currency(data.grand_total, data.currency)}</strong></div>
			${data.items_text ? `<div class="dip-summary-block"><strong>${__("Description")}</strong><pre>${frappe.utils.escape_html(strip_html(data.items_text))}</pre></div>` : ""}
			${data.students_text ? `<div class="dip-summary-block"><strong>${__("Learners")}</strong><pre>${frappe.utils.escape_html(data.students_text)}</pre></div>` : ""}
		`);
	}

	reset_form() {
		this.wrapper.find("#dip-has-certificates, #dip-has-cards").prop("checked", false);
		this.wrapper.find("#dip-receiver-name, #dip-contact-no, #dip-remarks").val("");
		this.wrapper.find("#dip-receiving-date").val(frappe.datetime.get_today());
		this.set_signature("");
	}

	show_form() {
		this.view = "form";
		this.$list.attr("hidden", true);
		this.wrapper.find(".dip-tabs, .dip-toolbar, #dip-list-footer, #dip-bulk-bar").attr("hidden", true);
		this.$form.removeAttr("hidden");
		this._signature_init_token = (this._signature_init_token || 0) + 1;
		const token = this._signature_init_token;
		requestAnimationFrame(() => {
			if (token !== this._signature_init_token) return;
			this.init_signature_pad();
		});
	}

	init_signature_pad() {
		dip_log("init_signature_pad", {
			has_teardown: !!this.signature_teardown,
			has_saved_data: !!this.signature_data,
		});
		if (this.signature_teardown) {
			dip_log("init_signature_pad destroy previous pad");
			this.signature_teardown.destroy();
			this.signature_teardown = null;
		}
		const canvas = this.wrapper.find("#dip-signature-canvas")[0];
		if (!canvas) {
			dip_log("init_signature_pad missing canvas");
			return;
		}
		if (!canvas.clientWidth) {
			dip_log("init_signature_pad waiting for layout", { clientWidth: canvas.clientWidth });
			requestAnimationFrame(() => this.init_signature_pad());
			return;
		}
		this.signature_teardown = bind_signature_canvas(canvas, {
			onInk: () => {
				setTimeout(() => this.wrapper.find("#dip-clear-sign").prop("disabled", false), 0);
			},
			onStrokeEnd: (dataUrl) => {
				this.signature_data = dataUrl;
				dip_log("stroke saved", { bytes: dataUrl.length, hasInk: this.signature_teardown?.hasInk() });
			},
		});
		if (this.signature_data) {
			dip_log("init_signature_pad restore saved signature");
			this.signature_teardown.load(this.signature_data);
			this.wrapper.find("#dip-clear-sign").prop("disabled", false);
		}
		dip_log("init_signature_pad ready", { size: this.signature_teardown.getSize() });
	}

	show_list() {
		this.view = "list";
		this.selected_invoice = null;
		if (this.signature_teardown) {
			this.signature_teardown.destroy();
			this.signature_teardown = null;
		}
		this.$form.attr("hidden", true);
		this.wrapper.find(".dip-tabs, .dip-toolbar, #dip-list-footer").removeAttr("hidden");
		this.wrapper.find("#dip-bulk-bar").removeAttr("hidden");
		this.$list.removeAttr("hidden");
		this.update_bulk_bar();
		if (this.active_tab === "pending") this.update_pending_footer();
	}

	set_signature(dataUrl) {
		dip_log("set_signature", { has_data: !!dataUrl, bytes: dataUrl ? dataUrl.length : 0 });
		this.signature_data = dataUrl || "";
		if (this.signature_teardown) {
			if (this.signature_data) {
				this.signature_teardown.load(this.signature_data);
			} else {
				this.signature_teardown.clear("set_signature");
			}
		}
		this.wrapper.find("#dip-clear-sign").prop("disabled", !this.signature_data);
	}

	capture_submission_context() {
		const info = {
			user_agent: navigator.userAgent || "",
			platform: navigator.platform || "",
			language: navigator.language || "",
			screen: `${window.screen?.width || 0}x${window.screen?.height || 0}`,
			viewport: `${window.innerWidth}x${window.innerHeight}`,
			timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
			captured_at: new Date().toISOString(),
		};

		return new Promise((resolve) => {
			if (!navigator.geolocation) {
				info.location_error = "Geolocation not supported";
				resolve({
					client_device_info: JSON.stringify(info),
				});
				return;
			}

			navigator.geolocation.getCurrentPosition(
				(pos) => {
					resolve({
						submission_latitude: pos.coords.latitude,
						submission_longitude: pos.coords.longitude,
						submission_location_accuracy: pos.coords.accuracy,
						client_device_info: JSON.stringify({
							...info,
							altitude: pos.coords.altitude,
							heading: pos.coords.heading,
							speed: pos.coords.speed,
						}),
					});
				},
				(err) => {
					info.location_error = err.message || __("Location permission denied");
					resolve({ client_device_info: JSON.stringify(info) });
				},
				{ enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
			);
		});
	}

	submit_acknowledgement() {
		if (!this.selected_invoice) return;
		const hasInk = this.signature_teardown?.hasInk();
		dip_log("submit", { hasInk, savedBytes: this.signature_data?.length || 0 });
		if (this.signature_teardown?.hasInk()) {
			this.signature_data = this.signature_teardown.toDataURL();
		} else if (!this.signature_data) {
			frappe.msgprint(__("Please draw the receiver signature first."));
			return;
		}

		this.capture_submission_context().then((capture) => {
			const payload = {
				sales_invoice: this.selected_invoice,
				receiver_name: this.wrapper.find("#dip-receiver-name").val(),
				receiving_date: this.wrapper.find("#dip-receiving-date").val(),
				contact_no: this.wrapper.find("#dip-contact-no").val(),
				has_certificates: this.wrapper.find("#dip-has-certificates").is(":checked") ? 1 : 0,
				has_cards: this.wrapper.find("#dip-has-cards").is(":checked") ? 1 : 0,
				receiver_signature: this.signature_data,
				remarks: this.wrapper.find("#dip-remarks").val(),
				submit: 1,
				...capture,
			};

			frappe.call({
				method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.save_acknowledgement",
				args: { data: payload },
				freeze: true,
				callback: (r) => {
					if (r.exc) return;
					frappe.show_alert({ message: __("Acknowledgement submitted"), indicator: "green" });
					const current = this.selected_invoice;
					this.delivery_queue = (this.delivery_queue || []).filter((name) => name !== current);
					if (this.delivery_queue.length) {
						frappe.show_alert({
							message: __("Opening next delivery ({0} remaining)", [this.delivery_queue.length]),
							indicator: "blue",
						});
						this.load_kpis();
						this.open_invoice(this.delivery_queue[0]);
						return;
					}
					this.clear_selection();
					this.show_list();
					this.load_kpis();
					this.load_active_tab();
				},
			});
		});
	}
}

function dip_show_assign_driver_dialog(sales_invoices, ondone) {
	const dialog = new frappe.ui.Dialog({
		title: __("Assign to Driver"),
		fields: [
			{
				fieldname: "driver",
				fieldtype: "Link",
				options: "User",
				label: __("Delivery Driver"),
				reqd: 1,
				get_query() {
					return {
						query: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.get_delivery_driver_users",
					};
				},
			},
		],
		primary_action_label: __("Assign"),
		primary_action(values) {
			frappe.call({
				method: "numerouno.numerouno.page.driver_invoice_portal.driver_invoice_portal.bulk_assign_delivery_driver",
				args: { sales_invoices, driver: values.driver },
				freeze: true,
				callback(r) {
					if (r.exc) return;
					const msg = r.message || {};
					let text = __("Assigned {0} invoice(s) to {1}", [msg.updated || 0, msg.driver_name || values.driver]);
					if (msg.skipped?.length) text += ` (${msg.skipped.length} skipped)`;
					frappe.show_alert({ message: text, indicator: "green" });
					dialog.hide();
					if (ondone) ondone();
				},
			});
		},
	});
	dialog.show();
}

function dip_log(...args) {
	console.log("[DIP]", ...args);
}

function bind_signature_canvas(canvas, callbacks) {
	const onInk = callbacks?.onInk;
	const onStrokeEnd = callbacks?.onStrokeEnd;
	const ratio = window.devicePixelRatio || 1;
	let displayWidth = 0;
	let displayHeight = 0;
	let drawing = false;
	let moved = false;
	let hasInk = false;
	let initialized = false;
	let ignoreMouseUntil = 0;
	let resizeTimer = null;
	const ctx = canvas.getContext("2d", { willReadFrequently: true });

	function applyStrokeStyle() {
		ctx.lineWidth = 2.5;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		ctx.strokeStyle = "#111";
		ctx.fillStyle = "#111";
	}

	function ensureSize(reason) {
		const width = Math.round(canvas.clientWidth || canvas.offsetWidth);
		const height = Math.round(canvas.clientHeight || 130);
		if (!width) {
			dip_log("ensureSize skipped", reason, { width, height });
			return false;
		}
		if (initialized && width === displayWidth && height === displayHeight) {
			return true;
		}

		let snapshot = null;
		if (hasInk && displayWidth > 0) {
			snapshot = canvas.toDataURL("image/png");
			dip_log("ensureSize snapshot", reason, { from: [displayWidth, displayHeight], to: [width, height] });
		}

		displayWidth = width;
		displayHeight = height;
		canvas.width = width * ratio;
		canvas.height = height * ratio;
		ctx.setTransform(1, 0, 0, 1, 0, 0);
		ctx.scale(ratio, ratio);
		applyStrokeStyle();
		initialized = true;
		dip_log("ensureSize applied", reason, { displayWidth, displayHeight, ratio });

		if (snapshot) {
			const img = new Image();
			img.onload = function () {
				ctx.drawImage(img, 0, 0, displayWidth, displayHeight);
				dip_log("ensureSize snapshot restored", reason);
			};
			img.onerror = function () {
				dip_log("ensureSize snapshot restore failed", reason);
			};
			img.src = snapshot;
		}
		return true;
	}

	function pointFromEvent(event) {
		const rect = canvas.getBoundingClientRect();
		const source = (event.touches && event.touches[0]) || (event.changedTouches && event.changedTouches[0]) || event;
		return { x: source.clientX - rect.left, y: source.clientY - rect.top };
	}

	function persistStroke(eventType) {
		if (!hasInk) return;
		const dataUrl = canvas.toDataURL("image/png");
		dip_log("persistStroke", eventType, { bytes: dataUrl.length, hasInk });
		if (onStrokeEnd) onStrokeEnd(dataUrl);
		if (onInk) onInk();
	}

	function shouldIgnoreMouse(event) {
		if (!event.type.startsWith("mouse")) return false;
		if (Date.now() < ignoreMouseUntil) {
			dip_log("ignore synthetic mouse", event.type);
			return true;
		}
		return false;
	}

	function startDraw(event) {
		if (!initialized) {
			dip_log("startDraw before init", event.type);
			return;
		}
		if (shouldIgnoreMouse(event)) return;
		if (event.type.startsWith("touch")) {
			ignoreMouseUntil = Date.now() + 700;
		}
		if (event.cancelable) event.preventDefault();
		event.stopPropagation();
		drawing = true;
		moved = false;
		const p = pointFromEvent(event);
		ctx.beginPath();
		ctx.moveTo(p.x, p.y);
		dip_log("startDraw", event.type, p);
	}

	function draw(event) {
		if (!drawing || shouldIgnoreMouse(event)) return;
		if (event.cancelable) event.preventDefault();
		moved = true;
		const p = pointFromEvent(event);
		ctx.lineTo(p.x, p.y);
		ctx.stroke();
		hasInk = true;
	}

	function endDraw(event) {
		if (!drawing || shouldIgnoreMouse(event)) return;
		if (event.cancelable) event.preventDefault();
		event.stopPropagation();
		drawing = false;
		if (!moved) {
			const p = pointFromEvent(event);
			ctx.beginPath();
			ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2);
			ctx.fill();
			hasInk = true;
		}
		dip_log("endDraw", event.type, { moved, hasInk });
		persistStroke(event.type);
	}

	const handlers = [
		["mousedown", startDraw], ["mousemove", draw], ["mouseup", endDraw],
		["touchstart", startDraw, { passive: false }], ["touchmove", draw, { passive: false }],
		["touchend", endDraw, { passive: false }], ["touchcancel", endDraw, { passive: false }],
	];
	handlers.forEach(([name, fn, opts]) => canvas.addEventListener(name, fn, opts || false));

	const resizeObserver = new ResizeObserver(() => {
		clearTimeout(resizeTimer);
		resizeTimer = setTimeout(() => {
			requestAnimationFrame(() => ensureSize("resize"));
		}, 120);
	});
	resizeObserver.observe(canvas);

	ensureSize("init");

	return {
		hasInk: () => hasInk,
		getSize: () => ({ displayWidth, displayHeight, initialized }),
		toDataURL: () => canvas.toDataURL("image/png"),
		clear(reason = "manual") {
			dip_log("clear", reason, { hadInk: hasInk });
			ctx.clearRect(0, 0, displayWidth, displayHeight);
			hasInk = false;
		},
		load(dataUrl) {
			if (!initialized) ensureSize("load");
			const img = new Image();
			img.onload = function () {
				ctx.clearRect(0, 0, displayWidth, displayHeight);
				ctx.drawImage(img, 0, 0, displayWidth, displayHeight);
				hasInk = true;
				dip_log("load complete", { bytes: dataUrl.length });
			};
			img.onerror = function () {
				dip_log("load failed", { bytes: dataUrl.length });
			};
			img.src = dataUrl;
		},
		destroy() {
			dip_log("destroy pad");
			resizeObserver.disconnect();
			clearTimeout(resizeTimer);
			handlers.forEach(([name, fn, opts]) => canvas.removeEventListener(name, fn, opts || false));
		},
	};
}
