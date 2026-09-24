// Supplier form — create Invoice Portal login user
frappe.ui.form.on("Supplier", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(__("Create Invoice Portal User"), () => {
			open_create_portal_user_dialog(frm);
		}, __("Portal"));

		frm.add_custom_button(__("Open Invoice Portal"), () => {
			window.open("/supplier-invoice-portal", "_blank");
		}, __("Portal"));
	},
});

function open_create_portal_user_dialog(frm) {
	const default_email =
		frm.doc.email_id ||
		(frm.doc.portal_users && frm.doc.portal_users[0] && frm.doc.portal_users[0].user) ||
		"";

	const d = new frappe.ui.Dialog({
		title: __("Create Supplier Invoice Portal User"),
		fields: [
			{
				fieldname: "email",
				fieldtype: "Data",
				label: __("Login Email"),
				options: "Email",
				reqd: 1,
				default: default_email,
			},
			{
				fieldname: "full_name",
				fieldtype: "Data",
				label: __("Full Name"),
				reqd: 1,
				default: frm.doc.supplier_name,
			},
			{
				fieldname: "password",
				fieldtype: "Password",
				label: __("Password"),
				reqd: 1,
			},
			{
				fieldname: "confirm_password",
				fieldtype: "Password",
				label: __("Confirm Password"),
				reqd: 1,
			},
			{
				fieldname: "send_email",
				fieldtype: "Check",
				label: __("Email login details to supplier"),
				default: 1,
			},
			{
				fieldtype: "HTML",
				options: `<p class="text-muted" style="margin-top:8px">
					Creates a Website User with the <b>Supplier</b> role, links it under Portal Users,
					and allows sign-in at <code>/supplier-invoice-portal</code>.
				</p>`,
			},
		],
		primary_action_label: __("Create User"),
		primary_action(values) {
			if ((values.password || "") !== (values.confirm_password || "")) {
				frappe.msgprint(__("Passwords do not match."));
				return;
			}
			if ((values.password || "").length < 8) {
				frappe.msgprint(__("Password must be at least 8 characters."));
				return;
			}
			d.hide();
			frappe.call({
				method: "numerouno.numerouno.api.supplier_portal.create_supplier_portal_user",
				args: {
					supplier: frm.doc.name,
					email: values.email,
					full_name: values.full_name,
					password: values.password,
					send_email: values.send_email ? 1 : 0,
				},
				freeze: true,
				freeze_message: __("Creating portal user…"),
				callback(r) {
					if (r.exc) return;
					frappe.show_alert({
						message: __("Portal user {0} created", [values.email]),
						indicator: "green",
					});
					frm.reload_doc();
				},
			});
		},
	});
	d.show();
}
