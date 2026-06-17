from numerouno.numerouno.asset_management import setup_asset_management_customizations


def execute():
	setup_asset_management_customizations()
	_set_allow_on_submit("Asset", "insurance_start_date")
	_set_allow_on_submit("Asset", "insurance_end_date")


def _set_allow_on_submit(doctype, fieldname):
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		doctype,
		fieldname,
		"allow_on_submit",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)
