import frappe


def execute():
    if not frappe.db.exists("DocType", "Overtime Request"):
        return

    _ensure_workflow_state("Draft", "Inverse")
    _ensure_workflow_state("Pending Direct Manager", "Info")
    _ensure_workflow_state("Pending Next Manager", "Warning")
    _ensure_workflow_state("Pending HR", "Primary")
    _ensure_workflow_state("Approved", "Success")
    _ensure_workflow_state("Rejected", "Danger")

    workflow_name = "Overtime Request Approval"
    if frappe.db.exists("Workflow", workflow_name):
        workflow = frappe.get_doc("Workflow", workflow_name)
        workflow.is_active = 1
    else:
        workflow = frappe.new_doc("Workflow")
        workflow.workflow_name = workflow_name
        workflow.document_type = "Overtime Request"
        workflow.is_active = 1
        workflow.send_email_alert = 1

    workflow.workflow_state_field = "workflow_state"
    workflow.override_status = 1
    workflow.update_field = "status"

    workflow.states = []
    workflow.transitions = []

    # Only Allow Edit For: single Role per state (Frappe workflow). Approvers use Employee like transitions;
    # Pending HR uses HR Manager; terminal states stay HR Manager so HR can correct records if needed.
    state_allow_edit = {
        "Draft": "Employee",
        "Pending Direct Manager": "Employee",
        "Pending Next Manager": "Employee",
        "Pending HR": "HR Manager",
        "Approved": "HR Manager",
        "Rejected": "HR Manager",
    }

    for state_name in (
        "Draft",
        "Pending Direct Manager",
        "Pending Next Manager",
        "Pending HR",
        "Approved",
        "Rejected",
    ):
        workflow.append(
            "states",
            {
                "state": state_name,
                "allow_edit": state_allow_edit[state_name],
                "update_value": state_name,
            },
        )

    transitions = [
        ("Draft", "Pending Direct Manager", "Submit for Approval", "Employee"),
        ("Draft", "Pending Direct Manager", "Submit for Approval", "Employee Self Service"),
        ("Draft", "Pending Direct Manager", "Submit for Approval", "System Manager"),
        (
            "Pending Direct Manager",
            "Pending Next Manager",
            "Approve as Direct Manager",
            "Employee",
        ),
        (
            "Pending Direct Manager",
            "Rejected",
            "Reject as Direct Manager",
            "Employee",
        ),
        (
            "Pending Direct Manager",
            "Pending Next Manager",
            "Approve as Direct Manager",
            "System Manager",
        ),
        (
            "Pending Direct Manager",
            "Rejected",
            "Reject as Direct Manager",
            "System Manager",
        ),
        (
            "Pending Next Manager",
            "Pending HR",
            "Approve as Next Manager",
            "Employee",
        ),
        (
            "Pending Next Manager",
            "Rejected",
            "Reject as Next Manager",
            "Employee",
        ),
        (
            "Pending Next Manager",
            "Pending HR",
            "Approve as Next Manager",
            "System Manager",
        ),
        (
            "Pending Next Manager",
            "Rejected",
            "Reject as Next Manager",
            "System Manager",
        ),
        ("Pending HR", "Approved", "Approve as HR", "HR Manager"),
        ("Pending HR", "Rejected", "Reject as HR", "HR Manager"),
        ("Pending HR", "Approved", "Approve as HR", "System Manager"),
        ("Pending HR", "Rejected", "Reject as HR", "System Manager"),
    ]

    action_names = sorted({row[2] for row in transitions})
    for action_name in action_names:
        _ensure_workflow_action(action_name)

    for state, next_state, action, role in transitions:
        workflow.append(
            "transitions",
            {
                "state": state,
                "action": action,
                "next_state": next_state,
                "allowed": role,
            },
        )

    workflow.save(ignore_permissions=True)


def _ensure_workflow_state(state_name, style):
    if frappe.db.exists("Workflow State", state_name):
        doc = frappe.get_doc("Workflow State", state_name)
        changed = False
        if doc.style != style:
            doc.style = style
            changed = True
        if changed:
            doc.save(ignore_permissions=True)
        return

    frappe.get_doc(
        {
            "doctype": "Workflow State",
            "workflow_state_name": state_name,
            "style": style,
        }
    ).insert(ignore_permissions=True)


def _ensure_workflow_action(action_name):
    if frappe.db.exists("Workflow Action Master", action_name):
        return

    frappe.get_doc(
        {
            "doctype": "Workflow Action Master",
            "workflow_action_name": action_name,
        }
    ).insert(ignore_permissions=True)
