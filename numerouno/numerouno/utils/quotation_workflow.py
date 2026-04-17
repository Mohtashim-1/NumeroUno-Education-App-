import frappe
from frappe import _
from frappe.model.workflow import get_transitions, get_workflow
from frappe.utils import cint


CANCELLATION_REASON_FIELD = "custom_cancellation_reason"


def require_cancellation_reason(doc, method=None):
	if (doc.get(CANCELLATION_REASON_FIELD) or "").strip():
		return

	frappe.throw(_("Please enter a cancellation reason before cancelling this quotation."))


@frappe.whitelist()
def is_cancellation_action(doctype, docname, action):
	doc = frappe.get_doc(doctype, docname)
	workflow = get_workflow(doctype)

	for transition in get_transitions(doc, workflow):
		if transition.action != action:
			continue

		return _is_cancel_state_in_workflow(workflow, transition.next_state)

	return False


@frappe.whitelist()
def save_cancellation_reason(doctype, docname, reason):
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Please enter a cancellation reason."))

	doc = frappe.get_doc(doctype, docname)
	doc.check_permission("write")
	doc.db_set(CANCELLATION_REASON_FIELD, reason, update_modified=True)
	return reason
def _is_cancel_state_in_workflow(workflow, state_name):
	state = next((row for row in workflow.states if row.state == state_name), None)
	return bool(state and cint(state.doc_status) == 2)
