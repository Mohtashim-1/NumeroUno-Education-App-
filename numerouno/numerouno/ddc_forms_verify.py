"""Health check for the DDC instructor course forms created from the ADNOC PDFs."""

import frappe

FORMS = {
	"DDC Candidate Prerequisite": "DDC Candidate Pre-Requisite Checklist",
	"DDC Micro Teaching Assessment": "DDC Micro Teaching Assessment Checklist",
	"DDC Written Assessment": "DDC Instructor Course Written Assessment",
	"DDC OMR Answer Sheet": "DDC Instructor Course OMR Answer Sheet",
	"DDC Practical Assessment": "DDC Instructor Course Practical Assessment Checklist",
}


def verify():
	for doctype, print_format in FORMS.items():
		exists = frappe.db.exists("DocType", doctype)
		if not exists:
			print(f"MISSING DOCTYPE: {doctype}")
			continue

		meta = frappe.get_meta(doctype)
		tables = [f"{df.fieldname}({df.options})" for df in meta.fields if df.fieldtype == "Table"]
		script = frappe.db.get_value(
			"Client Script", {"dt": doctype, "enabled": 1}, ["name", "script"], as_dict=True
		)
		pf = frappe.db.get_value(
			"Print Format", print_format, ["name", "disabled", "html"], as_dict=True
		)
		count = frappe.db.count(doctype)

		print(f"\n{doctype}")
		print(f"  fields: {len(meta.fields)} | child tables: {', '.join(tables) or 'none'}")
		print(f"  submittable: {bool(meta.is_submittable)} | existing docs: {count}")
		print(f"  client script: {script.name if script else 'NONE'}")
		if script:
			print(f"    loader event: {'onload' if 'onload(frm)' in script.script else 'setup/other'}")
		print(
			f"  print format: {pf.name if pf else 'MISSING'}"
			+ (f" | disabled={pf.disabled} | html={len(pf.html or '')} chars" if pf else "")
		)
