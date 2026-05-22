import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.assets.doctype.asset_maintenance.asset_maintenance import calculate_next_due_date


def _strip(value):
    return (value or "").strip()


def _get_filters(asset_category=None, location=None, department=None, status=None, criticality=None):
    asset_filters = {}
    maintenance_filters = {}

    asset_category = _strip(asset_category)
    location = _strip(location)
    department = _strip(department)
    status = _strip(status)
    criticality = _strip(criticality)

    if asset_category:
        asset_filters["asset_category"] = asset_category
        maintenance_filters["asset_category"] = asset_category
    if location:
        asset_filters["location"] = location
    if department:
        asset_filters["department"] = department
    if status:
        asset_filters["status"] = status
    if criticality:
        maintenance_filters["custom_criticality_rating"] = criticality

    return asset_filters, maintenance_filters


@frappe.whitelist()
def get_asset_management_portal_data(
    asset_category=None,
    location=None,
    department=None,
    status=None,
    criticality=None,
    asset_name=None,
    asset_limit=30,
    maintenance_limit=30,
    compliance_limit=30,
):
    asset_limit = int(asset_limit or 30)
    maintenance_limit = int(maintenance_limit or 30)
    compliance_limit = int(compliance_limit or 30)
    asset_filters, maintenance_filters = _get_filters(
        asset_category=asset_category,
        location=location,
        department=department,
        status=status,
        criticality=criticality,
    )
    asset_name = _strip(asset_name)
    if asset_name:
        asset_filters["name"] = asset_name
        maintenance_filters["asset_name"] = asset_name

    today = getdate(nowdate())
    next_30_days = add_days(today, 30)

    total_assets = frappe.db.count("Asset", filters=asset_filters)
    in_maintenance = frappe.db.count("Asset", filters={**asset_filters, "status": "In Maintenance"})
    overdue_tasks = frappe.db.count("Asset Maintenance Log", filters={"maintenance_status": "Overdue"})
    certificates_due = frappe.db.count(
        "Asset Maintenance Task",
        filters={
            "certificate_required": 1,
            "custom_certificate_expiry_date": ["between", [today, next_30_days]],
        },
    )

    assets = frappe.get_all(
        "Asset",
        filters=asset_filters,
        fields=[
            "name",
            "asset_name",
            "asset_category",
            "location",
            "department",
            "status",
            "custom_asset_tag_number",
            "custom_asset_type",
            "custom_manufacturer",
            "custom_model",
            "custom_serial_number",
            "custom_warranty_expiry_date",
            "custom_compliance_certificate_expiry",
            "custom_mtbf_hours",
            "custom_mttr_hours",
        ],
        order_by="modified desc",
        limit=asset_limit,
    )

    maintenance = frappe.get_all(
        "Asset Maintenance",
        filters=maintenance_filters,
        fields=[
            "name",
            "asset_name",
            "asset_category",
            "maintenance_team",
            "maintenance_manager_name",
            "custom_maintenance_strategy",
            "custom_criticality_rating",
            "custom_sla_expiry_date",
        ],
        order_by="modified desc",
        limit=maintenance_limit,
    )

    asset_names = [row.asset_name for row in maintenance if row.asset_name]
    asset_map = {}
    if asset_names:
        for row in frappe.get_all(
            "Asset",
            filters={"name": ["in", asset_names]},
            fields=["name", "asset_name", "location", "department", "status"],
        ):
            asset_map[row.name] = row

    for row in maintenance:
        asset = asset_map.get(row.asset_name) or {}
        row["asset_title"] = asset.get("asset_name")
        row["location"] = asset.get("location")
        row["department"] = asset.get("department")
        row["asset_status"] = asset.get("status")
        row["open_tasks"] = frappe.db.count(
            "Asset Maintenance Log",
            filters={"asset_maintenance": row.name, "maintenance_status": ["in", ["Planned", "Overdue"]]},
        )
        row["overdue_tasks"] = frappe.db.count(
            "Asset Maintenance Log",
            filters={"asset_maintenance": row.name, "maintenance_status": "Overdue"},
        )

    compliance_filters = {
        "certificate_required": 1,
        "custom_certificate_expiry_date": ["is", "set"],
    }
    if maintenance_filters:
        maintenance_names = frappe.get_all("Asset Maintenance", filters=maintenance_filters, pluck="name")
        if maintenance_names:
            compliance_filters["parent"] = ["in", maintenance_names]
        else:
            return {
                "metrics": {
                    "total_assets": total_assets,
                    "in_maintenance": in_maintenance,
                    "overdue_tasks": overdue_tasks,
                    "certificates_due": certificates_due,
                },
                "assets": assets,
                "maintenance": maintenance,
                "compliance": [],
            }

    compliance = frappe.get_all(
        "Asset Maintenance Task",
        filters=compliance_filters,
        fields=[
            "name",
            "parent",
            "maintenance_task",
            "maintenance_type",
            "periodicity",
            "next_due_date",
            "assign_to_name",
            "custom_certificate_expiry_date",
        ],
        order_by="custom_certificate_expiry_date asc",
        limit=compliance_limit,
    )

    parents = [row.parent for row in compliance if row.parent]
    parent_map = {}
    if parents:
        for row in frappe.get_all(
            "Asset Maintenance",
            filters={"name": ["in", parents]},
            fields=["name", "asset_name", "asset_category", "custom_criticality_rating"],
        ):
            parent_map[row.name] = row

    for row in compliance:
        parent = parent_map.get(row.parent) or {}
        row["asset_name"] = parent.get("asset_name")
        row["asset_category"] = parent.get("asset_category")
        row["criticality"] = parent.get("custom_criticality_rating")
        if row.custom_certificate_expiry_date:
            row["days_to_expiry"] = (getdate(row.custom_certificate_expiry_date) - today).days

    return {
        "metrics": {
            "total_assets": total_assets,
            "in_maintenance": in_maintenance,
            "overdue_tasks": overdue_tasks,
            "certificates_due": certificates_due,
        },
        "assets": assets,
        "maintenance": maintenance,
        "compliance": compliance,
    }


def _get_or_create_asset_maintenance(
    asset_name,
    maintenance_team=None,
    strategy=None,
    criticality=None,
    sla_response_time=None,
    sla_resolution_time=None,
    sla_expiry_date=None,
):
    asset = frappe.get_doc("Asset", asset_name)
    maintenance_name = frappe.db.get_value("Asset Maintenance", {"asset_name": asset_name})

    if maintenance_name:
        maintenance = frappe.get_doc("Asset Maintenance", maintenance_name)
        if maintenance_team:
            maintenance.maintenance_team = maintenance_team
    else:
        if not maintenance_team:
            frappe.throw("Maintenance Team is required to create Asset Maintenance.")
        maintenance = frappe.new_doc("Asset Maintenance")
        maintenance.asset_name = asset_name
        maintenance.company = asset.company
        maintenance.maintenance_team = maintenance_team

    if strategy is not None:
        maintenance.custom_maintenance_strategy = strategy
    if criticality is not None:
        maintenance.custom_criticality_rating = criticality
    if sla_response_time is not None:
        maintenance.custom_sla_response_time = sla_response_time
    if sla_resolution_time is not None:
        maintenance.custom_sla_resolution_time = sla_resolution_time
    if sla_expiry_date is not None:
        maintenance.custom_sla_expiry_date = sla_expiry_date

    return maintenance


def _append_task(
    maintenance,
    maintenance_task,
    maintenance_type,
    start_date,
    periodicity,
    assign_to,
    checklist=None,
    reminder_days_before=None,
    certificate_required=0,
    certificate_expiry_date=None,
    recertification_reminder_days=None,
):
    start_date = start_date or nowdate()
    next_due_date = calculate_next_due_date(periodicity=periodicity, start_date=start_date)
    return maintenance.append(
        "asset_maintenance_tasks",
        {
            "maintenance_task": maintenance_task,
            "maintenance_type": maintenance_type,
            "maintenance_status": "Planned",
            "start_date": start_date,
            "periodicity": periodicity,
            "assign_to": assign_to,
            "next_due_date": next_due_date,
            "certificate_required": certificate_required,
            "description": checklist,
            "custom_maintenance_checklist": checklist,
            "custom_send_due_reminder": 1,
            "custom_reminder_days_before": reminder_days_before,
            "custom_certificate_expiry_date": certificate_expiry_date,
            "custom_recertification_reminder_days": recertification_reminder_days,
        },
    )


@frappe.whitelist()
def create_asset_maintenance_from_portal(
    asset_name,
    maintenance_team,
    maintenance_task,
    assign_to,
    periodicity,
    maintenance_type="Preventive Maintenance",
    start_date=None,
    strategy=None,
    criticality=None,
    sla_response_time=None,
    sla_resolution_time=None,
    sla_expiry_date=None,
    reminder_days_before=None,
    checklist=None,
):
    asset_name = _strip(asset_name)
    if not asset_name:
        frappe.throw("Asset is required.")

    maintenance = _get_or_create_asset_maintenance(
        asset_name,
        maintenance_team=maintenance_team,
        strategy=strategy,
        criticality=criticality,
        sla_response_time=sla_response_time,
        sla_resolution_time=sla_resolution_time,
        sla_expiry_date=sla_expiry_date,
    )
    task = _append_task(
        maintenance,
        maintenance_task=maintenance_task,
        maintenance_type=maintenance_type,
        start_date=start_date,
        periodicity=periodicity,
        assign_to=assign_to,
        checklist=checklist,
        reminder_days_before=reminder_days_before,
    )
    maintenance.save(ignore_permissions=True)
    frappe.db.set_value("Asset", asset_name, "maintenance_required", 1, update_modified=False)
    frappe.db.commit()

    return {
        "asset_maintenance": maintenance.name,
        "asset_name": asset_name,
        "task": task.name,
    }


@frappe.whitelist()
def create_asset_compliance_from_portal(
    asset_name,
    maintenance_team,
    compliance_task,
    assign_to,
    certificate_expiry_date,
    periodicity="Yearly",
    start_date=None,
    criticality=None,
    checklist=None,
    recertification_reminder_days=30,
):
    asset_name = _strip(asset_name)
    if not asset_name:
        frappe.throw("Asset is required.")

    maintenance = _get_or_create_asset_maintenance(
        asset_name,
        maintenance_team=maintenance_team,
        strategy="Preventive",
        criticality=criticality,
    )
    task = _append_task(
        maintenance,
        maintenance_task=compliance_task,
        maintenance_type="Calibration",
        start_date=start_date,
        periodicity=periodicity,
        assign_to=assign_to,
        checklist=checklist,
        certificate_required=1,
        certificate_expiry_date=certificate_expiry_date,
        recertification_reminder_days=recertification_reminder_days,
    )
    maintenance.save(ignore_permissions=True)
    frappe.db.set_value("Asset", asset_name, "maintenance_required", 1, update_modified=False)
    frappe.db.commit()

    return {
        "asset_maintenance": maintenance.name,
        "asset_name": asset_name,
        "task": task.name,
    }
