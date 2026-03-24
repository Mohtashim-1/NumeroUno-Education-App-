import frappe
from frappe.utils import get_datetime, nowdate, nowtime


@frappe.whitelist()
def get_dashboard_data():
	active_entries = frappe.get_all(
		"Car Entry",
		filters={"status": "Active"},
		fields=["name", "vehicle", "driver_name", "entry_odometer", "entry_date", "entry_time"],
		order_by="modified desc",
	)

	logs = frappe.get_all(
		"Car Entry",
		fields=[
			"name",
			"vehicle",
			"driver_name",
			"entry_odometer",
			"exit_odometer",
			"entry_date",
			"entry_time",
			"exit_date",
			"exit_time",
			"entry_dashboard_image",
			"entry_vehicle_condition_image",
			"exit_dashboard_image",
			"exit_vehicle_condition_image",
		],
		order_by="modified desc",
		limit=50,
	)

	for row in logs:
		row["entry_stamp"] = format_stamp(row.get("entry_date"), row.get("entry_time"))
		row["exit_stamp"] = format_stamp(row.get("exit_date"), row.get("exit_time"))

	attach_driver_labels(active_entries)
	attach_driver_labels(logs)

	return {
		"active_entries": active_entries,
		"logs": logs,
	}


@frappe.whitelist()
def submit_entry(vehicle, driver_name, entry_odometer, entry_dashboard_image=None, entry_vehicle_condition_image=None):
	if not vehicle:
		frappe.throw("Please select a car.")

	active_name = frappe.db.get_value("Car Entry", {"vehicle": vehicle, "status": "Active"}, "name")
	if active_name:
		frappe.throw(f"Car {vehicle} already has an active entry: {active_name}.")

	doc = frappe.get_doc(
		{
			"doctype": "Car Entry",
			"vehicle": vehicle,
			"driver_name": driver_name,
			"entry_odometer": entry_odometer,
			"entry_date": nowdate(),
			"entry_time": nowtime(),
			"entry_dashboard_image": entry_dashboard_image,
			"entry_vehicle_condition_image": entry_vehicle_condition_image,
			"status": "Active",
		}
	)
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist()
def submit_exit(name, exit_odometer, exit_dashboard_image=None, exit_vehicle_condition_image=None):
	logger = frappe.logger("car_dashboard", allow_site=True)

	if not name:
		frappe.throw("Please select an active car.")

	doc = frappe.get_doc("Car Entry", name)
	logger.info(
		"submit_exit called | name=%s status=%s vehicle=%s stored_entry_odometer=%s incoming_exit_odometer=%s",
		doc.name,
		doc.status,
		doc.vehicle,
		doc.entry_odometer,
		exit_odometer,
	)
	if doc.status == "Exited":
		frappe.throw(f"Car entry {name} is already closed.")

	if exit_odometer in (None, ""):
		frappe.throw("Please enter Odometer Out.")

	doc.exit_odometer = exit_odometer
	doc.exit_date = nowdate()
	doc.exit_time = nowtime()
	doc.exit_dashboard_image = exit_dashboard_image
	doc.exit_vehicle_condition_image = exit_vehicle_condition_image
	doc.save()
	return {"name": doc.name}


def format_stamp(date_value, time_value):
	if not date_value:
		return ""
	if time_value:
		return get_datetime(f"{date_value} {time_value}").strftime("%b %d, %Y %I:%M %p")
	return get_datetime(f"{date_value} 00:00:00").strftime("%b %d, %Y")


def attach_driver_labels(rows):
	user_ids = sorted({row.get("driver_name") for row in rows if row.get("driver_name")})
	if not user_ids:
		return

	users = frappe.get_all(
		"User",
		filters={"name": ["in", user_ids]},
		fields=["name", "full_name"],
	)
	user_map = {user.name: user.full_name or user.name for user in users}

	for row in rows:
		driver_name = row.get("driver_name")
		row["driver_label"] = user_map.get(driver_name, driver_name)
