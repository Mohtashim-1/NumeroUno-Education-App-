import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, nowtime


class CarEntry(Document):
	def validate(self):
		logger = frappe.logger("car_entry", allow_site=True)
		self.driver_name = " ".join((self.driver_name or "").split())
		self.status = "Active"

		raw_entry_odometer = self.entry_odometer
		raw_exit_odometer = self.exit_odometer

		self.entry_odometer = cint(self.entry_odometer)
		if self.exit_odometer in (None, "", 0, "0"):
			self.exit_odometer = None
		else:
			self.exit_odometer = cint(self.exit_odometer)

		if not self.driver_name:
			frappe.throw("Driver Name is required.")

		if not self.entry_date:
			self.entry_date = nowdate()

		if not self.entry_time:
			self.entry_time = nowtime()

		if self.entry_odometer < 0:
			frappe.throw("Odometer In cannot be negative.")

		if self.is_new() and self.vehicle:
			last_record = frappe.db.get_value(
				"Car Entry",
				{"vehicle": self.vehicle},
				["name", "entry_odometer", "exit_odometer", "status"],
				order_by="creation desc",
				as_dict=True,
			)
			if last_record:
				last_known_odometer = cint(last_record.exit_odometer) if last_record.exit_odometer not in (None, "", 0, "0") else cint(last_record.entry_odometer)
				logger.info(
					"entry validation | vehicle=%s new_entry_odometer=%s last_record=%s last_status=%s last_known_odometer=%s",
					self.vehicle,
					self.entry_odometer,
					last_record.name,
					last_record.status,
					last_known_odometer,
				)
				if self.entry_odometer < last_known_odometer:
					frappe.throw(
						f"Odometer In ({self.entry_odometer}) cannot be less than the latest recorded odometer ({last_known_odometer}) for {self.vehicle}."
					)

		exit_started = (not self.is_new()) and any(
			[
				raw_exit_odometer not in (None, "", 0, "0"),
				self.exit_date,
				self.exit_time,
				self.exit_dashboard_image,
				self.exit_vehicle_condition_image,
			]
		)

		if exit_started:
			if not self.exit_date:
				self.exit_date = nowdate()
			if not self.exit_time:
				self.exit_time = nowtime()
			if self.exit_odometer is None:
				frappe.throw("Odometer Out is required when closing a car entry.")
			logger.info(
				"exit validation | name=%s vehicle=%s status=%s raw_entry_odometer=%s raw_exit_odometer=%s entry_odometer=%s exit_odometer=%s exit_date=%s exit_time=%s",
				self.name or "new",
				self.vehicle,
				self.status,
				raw_entry_odometer,
				raw_exit_odometer,
				self.entry_odometer,
				self.exit_odometer,
				self.exit_date,
				self.exit_time,
			)
			if self.exit_odometer < self.entry_odometer:
				logger.error(
					"exit validation failed | name=%s vehicle=%s entry_odometer=%s exit_odometer=%s",
					self.name or "new",
					self.vehicle,
					self.entry_odometer,
					self.exit_odometer,
				)
				frappe.throw(
					f"Odometer Out ({self.exit_odometer}) cannot be less than Odometer In ({self.entry_odometer})."
				)
			self.status = "Exited"


def cint(value):
	try:
		return int(value or 0)
	except (TypeError, ValueError):
		return 0
