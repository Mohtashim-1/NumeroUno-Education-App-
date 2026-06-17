import json

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import add_days, date_diff, flt, get_link_to_form, getdate, nowdate


def setup_asset_management_customizations():
    create_custom_fields(get_asset_custom_fields(), update=True)
    create_asset_dashboard_records()
    frappe.clear_cache()


def get_asset_custom_fields():
    return {
        "Asset": [
            {
                "fieldname": "custom_core_asset_information_section",
                "fieldtype": "Section Break",
                "label": "Core Asset Information",
                "insert_after": "department",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_asset_tag_number",
                "fieldtype": "Data",
                "label": "Asset Tag Number",
                "insert_after": "custom_core_asset_information_section",
                "unique": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "in_global_search": 1,
            },
            {
                "fieldname": "custom_asset_type",
                "fieldtype": "Select",
                "label": "Asset Type",
                "insert_after": "custom_asset_tag_number",
                "options": "\nElectrical\nMechanical\nIT\nVehicle\nFurniture\nBuilding\nTool\nOther",
                "in_standard_filter": 1,
            },
            {
                "fieldname": "custom_core_info_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_asset_type",
            },
            {
                "fieldname": "custom_manufacturer",
                "fieldtype": "Data",
                "label": "Manufacturer",
                "insert_after": "custom_core_info_column_break",
            },
            {
                "fieldname": "custom_model",
                "fieldtype": "Data",
                "label": "Model",
                "insert_after": "custom_manufacturer",
            },
            {
                "fieldname": "custom_serial_number",
                "fieldtype": "Data",
                "label": "Serial Number",
                "insert_after": "custom_model",
                "in_standard_filter": 1,
                "in_global_search": 1,
            },
            {
                "fieldname": "custom_commissioning_date",
                "fieldtype": "Date",
                "label": "Commissioning Date",
                "insert_after": "available_for_use_date",
            },
            {
                "fieldname": "custom_warranty_section",
                "fieldtype": "Section Break",
                "label": "Warranty Details",
                "insert_after": "custom_commissioning_date",
            },
            {
                "fieldname": "custom_warranty_expiry_date",
                "fieldtype": "Date",
                "label": "Warranty Expiry Date",
                "insert_after": "custom_warranty_section",
                "in_standard_filter": 1,
            },
            {
                "fieldname": "custom_warranty_coverage",
                "fieldtype": "Small Text",
                "label": "Warranty Coverage",
                "insert_after": "custom_warranty_expiry_date",
            },
            {
                "fieldname": "custom_warranty_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_warranty_coverage",
            },
            {
                "fieldname": "custom_warranty_vendor",
                "fieldtype": "Link",
                "label": "Warranty Vendor",
                "options": "Supplier",
                "insert_after": "custom_warranty_column_break",
            },
            {
                "fieldname": "custom_warranty_vendor_contact",
                "fieldtype": "Link",
                "label": "Warranty Vendor Contact",
                "options": "Contact",
                "insert_after": "custom_warranty_vendor",
            },
            {
                "fieldname": "custom_expected_life_and_depreciation_section",
                "fieldtype": "Section Break",
                "label": "Expected Life / Depreciation Info",
                "insert_after": "custom_warranty_vendor_contact",
            },
            {
                "fieldname": "custom_expected_life_years",
                "fieldtype": "Float",
                "label": "Expected Life (Years)",
                "insert_after": "custom_expected_life_and_depreciation_section",
            },
            {
                "fieldname": "custom_depreciation_notes",
                "fieldtype": "Small Text",
                "label": "Depreciation Notes",
                "insert_after": "custom_expected_life_years",
            },
            {
                "fieldname": "custom_performance_compliance_section",
                "fieldtype": "Section Break",
                "label": "Performance & Compliance",
                "insert_after": "maintenance_required",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_failure_history",
                "fieldtype": "Text Editor",
                "label": "Failure History",
                "insert_after": "custom_performance_compliance_section",
            },
            {
                "fieldname": "custom_mtbf_hours",
                "fieldtype": "Float",
                "label": "Mean Time Between Failures (Hours)",
                "insert_after": "custom_failure_history",
                "read_only": 1,
            },
            {
                "fieldname": "custom_performance_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_mtbf_hours",
            },
            {
                "fieldname": "custom_mttr_hours",
                "fieldtype": "Float",
                "label": "Mean Time To Repair (Hours)",
                "insert_after": "custom_performance_column_break",
                "read_only": 1,
            },
            {
                "fieldname": "custom_compliance_certificate",
                "fieldtype": "Attach",
                "label": "Compliance Certificate",
                "insert_after": "custom_mttr_hours",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_compliance_certificate_expiry",
                "fieldtype": "Date",
                "label": "Compliance Certificate Expiry",
                "insert_after": "custom_compliance_certificate",
                "in_standard_filter": 1,
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_inspection_report",
                "fieldtype": "Attach",
                "label": "Inspection Report",
                "insert_after": "custom_compliance_certificate_expiry",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_asset_documentation_section",
                "fieldtype": "Section Break",
                "label": "Attachments & Documentation",
                "insert_after": "custom_inspection_report",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_user_manual",
                "fieldtype": "Attach",
                "label": "User Manual",
                "insert_after": "custom_asset_documentation_section",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_maintenance_procedure",
                "fieldtype": "Attach",
                "label": "Maintenance Procedure",
                "insert_after": "custom_user_manual",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_safety_instructions",
                "fieldtype": "Attach",
                "label": "Safety Instructions",
                "insert_after": "custom_maintenance_procedure",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_documentation_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_safety_instructions",
            },
            {
                "fieldname": "custom_asset_photo",
                "fieldtype": "Attach Image",
                "label": "Asset Photo",
                "insert_after": "custom_documentation_column_break",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_asset_video",
                "fieldtype": "Attach",
                "label": "Asset Video",
                "insert_after": "custom_asset_photo",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_vendor_contract",
                "fieldtype": "Attach",
                "label": "Vendor Contract",
                "insert_after": "custom_asset_video",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_legal_documents_section",
                "fieldtype": "Section Break",
                "label": "Legal & Compliance Documents",
                "insert_after": "custom_vendor_contract",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_agreement_document",
                "fieldtype": "Attach",
                "label": "Agreement Document",
                "insert_after": "custom_legal_documents_section",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_agreement_expiry_date",
                "fieldtype": "Date",
                "label": "Agreement Expiry Date",
                "insert_after": "custom_agreement_document",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_legal_documents_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_agreement_expiry_date",
            },
            {
                "fieldname": "custom_insurance_document",
                "fieldtype": "Attach",
                "label": "Insurance Document",
                "insert_after": "custom_legal_documents_column_break",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_registration_document",
                "fieldtype": "Attach",
                "label": "Registration Document",
                "insert_after": "custom_insurance_document",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_registration_expiry_date",
                "fieldtype": "Date",
                "label": "Registration Expiry Date",
                "insert_after": "custom_registration_document",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_document_archive_section",
                "fieldtype": "Section Break",
                "label": "Document Archive",
                "insert_after": "custom_registration_expiry_date",
                "collapsible": 1,
            },
            {
                "fieldname": "custom_document_history",
                "fieldtype": "Table",
                "label": "Document History",
                "options": "Asset Document History",
                "insert_after": "custom_document_archive_section",
                "allow_on_submit": 1,
            },
        ],
        "Asset Maintenance": [
            {
                "fieldname": "custom_maintenance_planning_section",
                "fieldtype": "Section Break",
                "label": "Maintenance Planning",
                "insert_after": "maintenance_manager_name",
            },
            {
                "fieldname": "custom_maintenance_strategy",
                "fieldtype": "Select",
                "label": "Maintenance Strategy",
                "insert_after": "custom_maintenance_planning_section",
                "options": "\nPreventive\nPredictive\nCorrective\nCondition-based",
                "in_list_view": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "custom_criticality_rating",
                "fieldtype": "Select",
                "label": "Criticality Rating",
                "insert_after": "custom_maintenance_strategy",
                "options": "\nHigh\nMedium\nLow",
                "in_list_view": 1,
                "in_standard_filter": 1,
            },
            {
                "fieldname": "custom_planning_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_criticality_rating",
            },
            {
                "fieldname": "custom_sla_response_time",
                "fieldtype": "Duration",
                "label": "SLA Response Time",
                "insert_after": "custom_planning_column_break",
            },
            {
                "fieldname": "custom_sla_resolution_time",
                "fieldtype": "Duration",
                "label": "SLA Resolution Time",
                "insert_after": "custom_sla_response_time",
            },
            {
                "fieldname": "custom_sla_expiry_date",
                "fieldtype": "Date",
                "label": "SLA Expiry Date",
                "insert_after": "custom_sla_resolution_time",
                "in_standard_filter": 1,
            },
        ],
        "Asset Maintenance Task": [
            {
                "fieldname": "custom_maintenance_checklist",
                "fieldtype": "Text Editor",
                "label": "Maintenance Checklist",
                "insert_after": "description",
            },
            {
                "fieldname": "custom_reminder_settings_section",
                "fieldtype": "Section Break",
                "label": "Reminder Settings",
                "insert_after": "custom_maintenance_checklist",
            },
            {
                "fieldname": "custom_send_due_reminder",
                "fieldtype": "Check",
                "label": "Send Due Reminder",
                "insert_after": "custom_reminder_settings_section",
                "default": "1",
            },
            {
                "fieldname": "custom_reminder_days_before",
                "fieldtype": "Int",
                "label": "Reminder Days Before Due Date",
                "insert_after": "custom_send_due_reminder",
            },
            {
                "fieldname": "custom_reminder_column_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_reminder_days_before",
            },
            {
                "fieldname": "custom_certificate_expiry_date",
                "fieldtype": "Date",
                "label": "Certificate Expiry Date",
                "insert_after": "custom_reminder_column_break",
                "in_list_view": 1,
            },
            {
                "fieldname": "custom_recertification_reminder_days",
                "fieldtype": "Int",
                "label": "Recertification Reminder Days Before Expiry",
                "insert_after": "custom_certificate_expiry_date",
            },
        ],
        "Asset Maintenance Log": [
            {
                "fieldname": "custom_maintenance_checklist",
                "fieldtype": "Text Editor",
                "label": "Maintenance Checklist",
                "insert_after": "description",
                "read_only": 1,
            },
            {
                "fieldname": "custom_failure_observed",
                "fieldtype": "Check",
                "label": "Failure Observed",
                "insert_after": "custom_maintenance_checklist",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_failure_details",
                "fieldtype": "Text Editor",
                "label": "Failure Details",
                "insert_after": "custom_failure_observed",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_repair_duration",
                "fieldtype": "Duration",
                "label": "Repair Duration",
                "insert_after": "custom_failure_details",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_inspection_report",
                "fieldtype": "Attach",
                "label": "Inspection Report",
                "insert_after": "custom_repair_duration",
                "allow_on_submit": 1,
            },
            {
                "fieldname": "custom_certificate_expiry_date",
                "fieldtype": "Date",
                "label": "Certificate Expiry Date",
                "insert_after": "custom_inspection_report",
            },
        ],
    }


def sync_asset_maintenance_log_custom_fields(doc, method=None):
    for task in doc.get("asset_maintenance_tasks") or []:
        log_name = frappe.db.get_value(
            "Asset Maintenance Log",
            {
                "asset_maintenance": doc.name,
                "task": task.name,
                "maintenance_status": ("in", ["Planned", "Overdue"]),
            },
        )
        if not log_name:
            continue

        frappe.db.set_value(
            "Asset Maintenance Log",
            log_name,
            {
                "custom_maintenance_checklist": task.get("custom_maintenance_checklist"),
                "custom_certificate_expiry_date": task.get("custom_certificate_expiry_date"),
            },
            update_modified=False,
        )


def update_asset_performance_from_log(doc, method=None):
    if not doc.asset_name:
        return

    failure_logs = frappe.get_all(
        "Asset Maintenance Log",
        fields=["completion_date", "custom_repair_duration"],
        filters={
            "asset_name": doc.asset_name,
            "docstatus": 1,
            "maintenance_status": "Completed",
            "custom_failure_observed": 1,
            "completion_date": ("is", "set"),
        },
        order_by="completion_date asc",
    )
    if not failure_logs:
        return

    mtbf_hours = 0
    if len(failure_logs) > 1:
        total_days_between_failures = sum(
            date_diff(failure_logs[idx].completion_date, failure_logs[idx - 1].completion_date)
            for idx in range(1, len(failure_logs))
        )
        mtbf_hours = flt(total_days_between_failures * 24 / (len(failure_logs) - 1), 2)

    repair_durations = [flt(log.custom_repair_duration) for log in failure_logs if log.custom_repair_duration]
    mttr_hours = flt(sum(repair_durations) / len(repair_durations) / 3600, 2) if repair_durations else 0

    frappe.db.set_value(
        "Asset",
        doc.asset_name,
        {
            "custom_mtbf_hours": mtbf_hours,
            "custom_mttr_hours": mttr_hours,
        },
        update_modified=False,
    )


def send_asset_maintenance_reminders():
    send_due_maintenance_reminders()
    send_sla_expiry_reminders()
    send_certificate_recertification_reminders()


def send_due_maintenance_reminders():
    today = getdate(nowdate())
    for task in frappe.get_all(
        "Asset Maintenance Task",
        fields=["name", "parent", "maintenance_task", "assign_to", "next_due_date", "periodicity"],
        filters={"maintenance_status": ("in", ["Planned", "Overdue"]), "custom_send_due_reminder": 1},
    ):
        if not task.next_due_date:
            continue

        reminder_days = frappe.db.get_value("Asset Maintenance Task", task.name, "custom_reminder_days_before")
        if reminder_days is None:
            reminder_days = get_default_reminder_days(task.periodicity)

        if add_days(today, int(reminder_days or 0)) != getdate(task.next_due_date):
            continue

        maintenance = frappe.get_doc("Asset Maintenance", task.parent)
        recipients = get_recipients_for_users([task.assign_to, maintenance.maintenance_manager])
        if recipients:
            send_asset_reminder_email(
                recipients,
                _("Asset Maintenance Due"),
                _("Maintenance task {0} for asset {1} is due on {2}.").format(
                    frappe.bold(task.maintenance_task),
                    get_link_to_form("Asset", maintenance.asset_name),
                    frappe.bold(task.next_due_date),
                ),
                "Asset Maintenance",
                maintenance.name,
            )


def send_sla_expiry_reminders():
    target_date = add_days(getdate(nowdate()), 30)
    for maintenance in frappe.get_all(
        "Asset Maintenance",
        fields=["name", "asset_name", "maintenance_manager", "custom_sla_expiry_date"],
        filters={"custom_sla_expiry_date": target_date},
    ):
        recipients = get_recipients_for_users([maintenance.maintenance_manager])
        if recipients:
            send_asset_reminder_email(
                recipients,
                _("Asset Maintenance SLA Expiring"),
                _("SLA for asset {0} expires on {1}.").format(
                    get_link_to_form("Asset", maintenance.asset_name),
                    frappe.bold(maintenance.custom_sla_expiry_date),
                ),
                "Asset Maintenance",
                maintenance.name,
            )


def send_certificate_recertification_reminders():
    today = getdate(nowdate())
    reminder_roles = {
        30: ("QA", "Quality Manager"),
        15: ("Training Manager",),
        7: ("Business Support Manager", "Business support manager"),
        0: ("GM",),
    }

    for task in frappe.get_all(
        "Asset Maintenance Task",
        fields=[
            "name",
            "parent",
            "maintenance_task",
            "assign_to",
            "custom_certificate_expiry_date",
            "custom_recertification_reminder_days",
        ],
        filters={"certificate_required": 1, "custom_certificate_expiry_date": ("is", "set")},
    ):
        days_until_expiry = (getdate(task.custom_certificate_expiry_date) - today).days
        if days_until_expiry < 0:
            continue

        custom_days = task.custom_recertification_reminder_days
        if custom_days is not None and days_until_expiry == int(custom_days):
            roles = ()
        elif days_until_expiry in reminder_roles:
            roles = reminder_roles[days_until_expiry]
        else:
            continue

        maintenance = frappe.get_doc("Asset Maintenance", task.parent)
        recipients = get_recipients_for_users([task.assign_to, maintenance.maintenance_manager])
        recipients.extend(get_recipients_for_roles(roles))
        recipients = list(dict.fromkeys(filter(None, recipients)))
        if recipients:
            send_asset_reminder_email(
                recipients,
                _("Asset Certificate Recertification Due"),
                _("Certificate for task {0} on asset {1} expires on {2}.").format(
                    frappe.bold(task.maintenance_task),
                    get_link_to_form("Asset", maintenance.asset_name),
                    frappe.bold(task.custom_certificate_expiry_date),
                ),
                "Asset Maintenance",
                maintenance.name,
            )


def get_default_reminder_days(periodicity):
    return {
        "Daily": 0,
        "Weekly": 1,
        "Monthly": 7,
        "Quarterly": 14,
        "Half-yearly": 30,
        "Yearly": 30,
        "2 Yearly": 30,
        "3 Yearly": 30,
    }.get(periodicity, 7)


def get_recipients_for_users(users):
    recipients = []
    for user in users:
        if not user:
            continue
        recipients.append(frappe.db.get_value("User", user, "email") or user)
    return list(dict.fromkeys(filter(None, recipients)))


def get_recipients_for_roles(roles):
    if not roles:
        return []
    users = frappe.get_all(
        "Has Role",
        filters={"role": ("in", roles), "parenttype": "User"},
        pluck="parent",
    )
    return get_recipients_for_users(users)


def send_asset_reminder_email(recipients, subject, message, reference_doctype, reference_name):
    frappe.sendmail(
        recipients=recipients,
        subject=subject,
        message=message,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        now=False,
    )


def create_asset_dashboard_records():
    for doc in get_number_cards() + get_dashboard_charts():
        upsert_doc(doc)

    upsert_doc(get_asset_management_dashboard())
    upsert_doc(get_asset_management_workspace())


def get_number_cards():
    return [
        {
            "doctype": "Number Card",
            "name": "Open Maintenance Tasks",
            "label": "Open Maintenance Tasks",
            "document_type": "Asset Maintenance Log",
            "function": "Count",
            "type": "Document Type",
            "filters_json": json.dumps([["Asset Maintenance Log", "maintenance_status", "=", "Planned", False]]),
            "is_public": 1,
            "is_standard": 0,
            "module": "Numerouno",
        },
        {
            "doctype": "Number Card",
            "name": "Overdue Maintenance Tasks",
            "label": "Overdue Maintenance Tasks",
            "document_type": "Asset Maintenance Log",
            "function": "Count",
            "type": "Document Type",
            "filters_json": json.dumps([["Asset Maintenance Log", "maintenance_status", "=", "Overdue", False]]),
            "is_public": 1,
            "is_standard": 0,
            "module": "Numerouno",
        },
        {
            "doctype": "Number Card",
            "name": "Certificates Requiring Renewal",
            "label": "Certificates Requiring Renewal",
            "document_type": "Asset Maintenance Task",
            "parent_document_type": "Asset Maintenance",
            "function": "Count",
            "type": "Document Type",
            "filters_json": json.dumps([["Asset Maintenance Task", "certificate_required", "=", 1, False]]),
            "is_public": 1,
            "is_standard": 0,
            "module": "Numerouno",
        },
    ]


def get_dashboard_charts():
    return [
        {
            "doctype": "Dashboard Chart",
            "name": "Maintenance Status",
            "chart_name": "Maintenance Status",
            "chart_type": "Group By",
            "document_type": "Asset Maintenance Log",
            "group_by_based_on": "maintenance_status",
            "group_by_type": "Count",
            "type": "Donut",
            "timeseries": 0,
            "filters_json": "[]",
            "custom_options": json.dumps({"type": "donut", "height": 300}),
            "is_public": 1,
            "is_standard": 0,
            "module": "Numerouno",
        },
        {
            "doctype": "Dashboard Chart",
            "name": "Asset Criticality",
            "chart_name": "Asset Criticality",
            "chart_type": "Group By",
            "document_type": "Asset Maintenance",
            "group_by_based_on": "custom_criticality_rating",
            "group_by_type": "Count",
            "type": "Bar",
            "timeseries": 0,
            "filters_json": "[]",
            "custom_options": json.dumps({"type": "bar", "height": 300}),
            "is_public": 1,
            "is_standard": 0,
            "module": "Numerouno",
        },
    ]


def get_asset_management_dashboard():
    return {
        "doctype": "Dashboard",
        "name": "Asset Management",
        "dashboard_name": "Asset Management",
        "is_default": 0,
        "is_standard": 0,
        "module": "Numerouno",
        "cards": [
            {"card": "Open Maintenance Tasks"},
            {"card": "Overdue Maintenance Tasks"},
            {"card": "Certificates Requiring Renewal"},
        ],
        "charts": [
            {"chart": "Maintenance Status", "width": "Half"},
            {"chart": "Asset Criticality", "width": "Half"},
        ],
    }


def get_asset_management_workspace():
    content = [
        {"type": "number_card", "data": {"card_name": "Total Assets", "col": 3}},
        {"type": "number_card", "data": {"card_name": "Open Maintenance Tasks", "col": 3}},
        {"type": "number_card", "data": {"card_name": "Overdue Maintenance Tasks", "col": 3}},
        {"type": "number_card", "data": {"card_name": "Certificates Requiring Renewal", "col": 3}},
        {"type": "chart", "data": {"chart_name": "Maintenance Status", "col": 6}},
        {"type": "chart", "data": {"chart_name": "Asset Criticality", "col": 6}},
        {"type": "shortcut", "data": {"shortcut_name": "Asset", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "Asset Maintenance", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "Maintenance Log", "col": 3}},
        {"type": "shortcut", "data": {"shortcut_name": "Asset Portal", "col": 3}},
    ]
    return {
        "doctype": "Workspace",
        "name": "Asset Management",
        "label": "Asset Management",
        "title": "Asset Management",
        "module": "Numerouno",
        "parent_page": "Assets",
        "public": 1,
        "is_hidden": 0,
        "icon": "assets",
        "content": json.dumps(content, separators=(",", ":")),
        "number_cards": [
            {"label": "Total Assets", "number_card_name": "Total Assets"},
            {"label": "Open Maintenance Tasks", "number_card_name": "Open Maintenance Tasks"},
            {"label": "Overdue Maintenance Tasks", "number_card_name": "Overdue Maintenance Tasks"},
            {"label": "Certificates Requiring Renewal", "number_card_name": "Certificates Requiring Renewal"},
        ],
        "charts": [
            {"label": "Maintenance Status", "chart_name": "Maintenance Status"},
            {"label": "Asset Criticality", "chart_name": "Asset Criticality"},
        ],
        "shortcuts": [
            {"label": "Asset", "link_to": "Asset", "type": "DocType"},
            {"label": "Asset Maintenance", "link_to": "Asset Maintenance", "type": "DocType"},
            {"label": "Maintenance Log", "link_to": "Asset Maintenance Log", "type": "DocType"},
            {"label": "Asset Portal", "link_to": "asset-management-portal", "type": "Page"},
        ],
    }


def upsert_doc(data):
    if frappe.db.exists(data["doctype"], data["name"]):
        if data["doctype"] in ("Dashboard", "Dashboard Chart", "Number Card"):
            frappe.db.set_value(data["doctype"], data["name"], "is_standard", 0, update_modified=False)
        doc = frappe.get_doc(data["doctype"], data["name"])
        doc.update(data)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc(data).insert(ignore_permissions=True)
