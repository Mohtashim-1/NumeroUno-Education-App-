import frappe
from frappe import _
from frappe.model.workflow import get_transitions, get_workflow
from frappe.utils import cint


CANCELLATION_REASON_FIELD = "custom_cancellation_reason"
CANCELLED_WORKFLOW_STATE = "Cancelled"


def require_cancellation_reason(doc, method=None):
	if (doc.get(CANCELLATION_REASON_FIELD) or "").strip():
		return

	frappe.throw(_("Please enter a cancellation reason before cancelling this quotation."))


def sync_workflow_state_on_cancel(doc, method=None):
	"""Keep workflow_state in sync when Quotation is cancelled via Cancel button (not workflow action).

	Native cancel sets docstatus=2 but leaves workflow_state (e.g. Approved) unchanged.
	"""
	if cint(doc.docstatus) != 2:
		return

	current = (doc.get("workflow_state") or "").strip()
	if current == CANCELLED_WORKFLOW_STATE:
		return

	try:
		workflow = get_workflow(doc.doctype)
	except Exception:
		return

	has_cancelled = any(row.state == CANCELLED_WORKFLOW_STATE for row in (workflow.states or []))
	if not has_cancelled:
		return

	doc.db_set("workflow_state", CANCELLED_WORKFLOW_STATE, update_modified=False)
	doc.workflow_state = CANCELLED_WORKFLOW_STATE


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
