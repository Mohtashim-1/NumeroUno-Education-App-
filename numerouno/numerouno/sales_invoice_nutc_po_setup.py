"""Embed Customer PO attachment pages in Sales Invoice NUTC print/PDF."""

from __future__ import annotations

import frappe

PRINT_NAME = "Sales Invoice NUTC"

PO_BLOCK_MARKER = "{# LAST PAGE: CUSTOMER PO ATTACHMENT"

PO_BLOCK = r'''{# ===================================================== #}
{# LAST PAGE: CUSTOMER PO ATTACHMENT                     #}
{# Render attached PDF pages (or images) inside print/PDF. #}
{# Falls back to Student Group attachment when SI field is empty. #}
{# ===================================================== #}

{% set po_files = [] %}
{% if doc.get("custom_customer_po_attachment") %}
  {% set _ = po_files.append(doc.custom_customer_po_attachment) %}
{% endif %}
{% if not po_files and doc.select_student_group %}
  {% for selected_group in doc.select_student_group %}
    {% if selected_group.student_group %}
      {% set sg_po = frappe.db.get_value("Student Group", selected_group.student_group, "custom_customer_po_attachment") %}
      {% if sg_po and sg_po not in po_files %}
        {% set _ = po_files.append(sg_po) %}
      {% endif %}
    {% endif %}
  {% endfor %}
{% endif %}

{% if po_files %}
    {% set po_attachment = po_files[0] %}
    {% set po_attachment_url = frappe.utils.get_url(po_attachment) %}
    {% set po_extension = po_attachment.split("?")[0].split(".")[-1].lower() %}

    {% if po_extension in ["jpg", "jpeg", "png", "webp"] %}
        <div class="force-new-page po-attachment-page"
             style="width:100%; text-align:center; padding:10px; box-sizing:border-box;">
            <h3 style="margin-bottom:15px;">CUSTOMER PURCHASE ORDER</h3>
            <img src="{{ po_attachment_url }}"
                 alt="Customer Purchase Order"
                 style="display:block; width:100%; max-width:100%; max-height:1040px; margin:0 auto; object-fit:contain;" />
        </div>
    {% elif po_extension == "pdf" %}
        {% set po_pages = po_attachment | pdf_to_images %}
        {% if po_pages %}
            {% for page_img in po_pages %}
                <div class="force-new-page po-attachment-page"
                     style="width:100%; text-align:center; padding:8px; box-sizing:border-box;">
                    {% if loop.first %}
                    <h3 style="margin-bottom:10px;">CUSTOMER PURCHASE ORDER</h3>
                    {% endif %}
                    <img src="{{ page_img }}"
                         alt="Customer Purchase Order page {{ loop.index }}"
                         style="display:block; width:100%; max-width:100%; max-height:1040px; margin:0 auto; object-fit:contain;" />
                </div>
            {% endfor %}
        {% else %}
            <div class="force-new-page po-attachment-page"
                 style="width:100%; text-align:center; padding:10px; box-sizing:border-box;">
                <h3 style="margin-bottom:15px;">CUSTOMER PURCHASE ORDER</h3>
                <p style="margin-top:50px;">Customer Purchase Order is attached as a PDF.</p>
                <p><a href="{{ po_attachment_url }}">Open Customer Purchase Order</a></p>
            </div>
        {% endif %}
    {% else %}
        <div class="force-new-page po-attachment-page"
             style="width:100%; text-align:center; padding:10px; box-sizing:border-box;">
            <h3 style="margin-bottom:15px;">CUSTOMER PURCHASE ORDER</h3>
            <p><a href="{{ po_attachment_url }}">Open Customer PO Attachment</a></p>
        </div>
    {% endif %}
{% endif %}
'''


def _fixture_html() -> str:
	from pathlib import Path
	import json

	path = Path(__file__).parent / "print_format/sales_invoice_nutc/sales_invoice_nutc.json"
	return json.loads(path.read_text()).get("html") or ""


def _strip_old_po_block(html: str) -> str:
	marker_pos = html.find("LAST PAGE: CUSTOMER PO ATTACHMENT")
	if marker_pos < 0:
		return html.rstrip()

	start = html.rfind("{#", 0, marker_pos)
	prev = html.rfind("{#", 0, start)
	if prev >= 0 and "=====" in html[prev:start]:
		start = prev

	footer_idx = html.find('<div class="col-md-12" style="margin-top:10px;">', start)
	if footer_idx > start:
		endif_before_footer = html.rfind("{% endif %}", start, footer_idx)
		if endif_before_footer >= start:
			return (html[:start] + html[endif_before_footer + len("{% endif %}") :]).rstrip()

	return html[:start].rstrip()


def ensure():
	if not frappe.db.exists("Print Format", PRINT_NAME):
		frappe.throw(f"Print Format {PRINT_NAME} not found")

	# Always rebuild from the app fixture so a previous bad patch cannot accumulate.
	html = _strip_old_po_block(_fixture_html())
	html = html.rstrip() + "\n\n" + PO_BLOCK.strip() + "\n"
	frappe.get_jenv().from_string(html)
	frappe.db.set_value("Print Format", PRINT_NAME, "html", html, update_modified=True)
	frappe.db.commit()
	return {
		"print_format": PRINT_NAME,
		"has_pdf_to_images": "pdf_to_images" in html,
		"html_length": len(html),
	}


def verify(invoice="ACC-SINV-2026-25469"):
	from numerouno.numerouno.utils.pdf_to_img import _get_file_path, pdf_to_base64_images

	meta = frappe.get_meta("Sales Invoice")
	has_field = bool(meta.get_field("custom_customer_po_attachment"))
	doc = frappe.get_doc("Sales Invoice", invoice)
	url = doc.get("custom_customer_po_attachment") if has_field else None
	groups = []
	for row in doc.get("select_student_group") or []:
		sg = row.student_group
		po = frappe.db.get_value("Student Group", sg, "custom_customer_po_attachment")
		groups.append({"student_group": sg, "po": po})
		if not url and po:
			url = po
	pages = pdf_to_base64_images(url) if url else []
	html = frappe.db.get_value("Print Format", PRINT_NAME, "html") or ""
	rendered = frappe.get_print(
		"Sales Invoice",
		invoice,
		print_format=PRINT_NAME,
		no_letterhead=0,
	)
	return {
		"invoice": invoice,
		"si_has_field": has_field,
		"po_url": url,
		"file_path": _get_file_path(url) if url else None,
		"groups": groups,
		"page_count": len(pages),
		"page0_bytes": len(pages[0]) if pages else 0,
		"html_has_filter": "pdf_to_images" in html,
		"rendered_po_pages": rendered.count("po-attachment-page"),
		"rendered_has_pdf_link_fallback": "Open Customer Purchase Order" in rendered,
		"rendered_has_heading": "CUSTOMER PURCHASE ORDER" in rendered,
	}


def sync_json():
	"""Keep the app fixture in sync with the live Print Format HTML."""
	from pathlib import Path
	import json

	path = Path(__file__).parent / "print_format/sales_invoice_nutc/sales_invoice_nutc.json"
	html = frappe.db.get_value("Print Format", PRINT_NAME, "html") or ""
	data = json.loads(path.read_text())
	data["html"] = html
	path.write_text(json.dumps(data, indent=1) + "\n")
	return {"path": str(path), "html_length": len(html), "has_filter": "pdf_to_images" in html}


def after_migrate():
	try:
		ensure()
	except Exception:
		frappe.log_error(title="Sales Invoice NUTC PO attachment print setup")
