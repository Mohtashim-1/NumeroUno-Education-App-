import frappe


def execute():
    """Fix Overtime Request workflow: allow_edit was System Manager for all states, locking out approvers."""
    name = "Overtime Request Approval"
    if not frappe.db.exists("Workflow", name):
        return

    workflow = frappe.get_doc("Workflow", name)
    state_allow_edit = {
        "Draft": "Employee",
        "Pending Direct Manager": "Employee",
        "Pending Next Manager": "Employee",
        "Pending HR": "HR Manager",
        "Approved": "HR Manager",
        "Rejected": "HR Manager",
    }

    changed = False
    for row in workflow.states:
        want = state_allow_edit.get(row.state)
        if want and row.allow_edit != want:
            row.allow_edit = want
            changed = True

    if changed:
        workflow.save(ignore_permissions=True)
