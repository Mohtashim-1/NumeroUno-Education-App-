// Copyright (c) 2026, mohtashim and contributors
// For license information, please see license.txt

const IQA_DEBUG = true;

function iqa_log(event, data) {
	if (!IQA_DEBUG) return;
	console.log(`[IQA] ${event}`, data);
}

function iqa_snapshot(frm) {
	return {
		docname: frm.doc.name,
		docstatus: frm.doc.docstatus,
		owner: frm.doc.owner,
		user: frappe.session.user,
		is_new: frm.is_new(),
		has_write: frm.has_perm("write"),
		has_submit: frm.has_perm("submit"),
		frm_read_only: frm.read_only,
		is_dirty: frm.is_dirty(),
	};
}

function apply_iqa_edit_state(frm, reason) {
	const submitted = cint(frm.doc.docstatus) === 1;
	const can_edit = frm.has_perm("write") && !submitted;

	iqa_log("apply_edit_state", { reason, submitted, can_edit, ...iqa_snapshot(frm) });

	if (submitted) {
		if (!frm.read_only) {
			frm.set_read_only(true);
			iqa_log("locked_submitted", { docname: frm.doc.name });
		}
		return;
	}

	// Draft: only unlock if something incorrectly locked the form.
	if (can_edit && frm.read_only) {
		frm.set_read_only(false);
		iqa_log("unlocked_draft", { docname: frm.doc.name, reason });
	}

	// Re-enable text editors if a previous script disabled them.
	if (can_edit) {
		frm.page.wrapper
			.find(".ql-editor")
			.attr("contenteditable", true)
			.removeClass("disabled");
	}
}

frappe.ui.form.on("Internal Quality Assurance", {
	onload(frm) {
		iqa_log("onload", iqa_snapshot(frm));
	},

	refresh(frm) {
		iqa_log("refresh_start", iqa_snapshot(frm));

		setTimeout(() => {
			frm.page.wrapper.find(".form-footer").hide();
		}, 300);

		apply_iqa_edit_state(frm, "refresh");

		iqa_log("refresh_end", iqa_snapshot(frm));
	},

	before_save(frm) {
		iqa_log("before_save", iqa_snapshot(frm));
	},

	after_save(frm) {
		iqa_log("after_save", iqa_snapshot(frm));
		apply_iqa_edit_state(frm, "after_save");
	},

	on_submit(frm) {
		iqa_log("on_submit", iqa_snapshot(frm));
		apply_iqa_edit_state(frm, "on_submit");
	},

	after_submit(frm) {
		iqa_log("after_submit", iqa_snapshot(frm));
		apply_iqa_edit_state(frm, "after_submit");
	},
});
